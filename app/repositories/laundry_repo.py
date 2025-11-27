import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, update, delete, and_, func, extract, Integer
from sqlalchemy.ext.asyncio import AsyncSession


from app.db.base import async_session
from app.db.models.residents import Resident as User
from app.db.models.machine import Machine as Machine
from app.db.models.booking import Booking as Booking
from app.db.models.room import rooms as Room

# ==========================================
# РАБОТА С ПОЛЬЗОВАТЕЛЯМИ (АУТЕНТИФИКАЦИЯ)
# ==========================================

async def get_user_by_tg_id(tg_id: int):
    """Проверка: есть ли пользователь с таким TG ID в базе"""
    async with async_session() as session:
        query = select(User).where(User.tg_id == tg_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()


async def find_resident_by_fio(fio_parts: list[str]):
    """
    Поиск резидента по ФИО.
    fio_parts: список ['Фамилия', 'Имя', 'Отчество']
    """
    # Если ввели меньше 3 слов, поиск невозможен
    if len(fio_parts) < 3:
        return None

    last_name = fio_parts[0]
    first_name = fio_parts[1]
    patronymic = fio_parts[2]

    async with async_session() as session:
        query = select(User).where(
            User.last_name == last_name,
            User.first_name == first_name,
            User.patronymic == patronymic
        )
        result = await session.execute(query)
        
        # Получаем всех найденных (на случай полных тезок)
        found_users = result.scalars().all()
        
        if len(found_users) == 1:
            return found_users[0]
        elif len(found_users) > 1:
            # Если найдено несколько тезок, возвращаем None,
            # чтобы бот запросил поиск по зачетке (для точности)
            return None
        else:
            return None


async def find_resident_by_id_card(id_card: int):
    """Поиск резидента по номеру зачетной книжки / пропуска"""
    async with async_session() as session:
        query = select(User).where(User.idcards == id_card)
        result = await session.execute(query)
        return result.scalar_one_or_none()


async def activate_resident_user(resident_id: int, tg_id: int):
    """
    Привязывает Telegram ID к найденному резиденту.
    Возвращает обновленный объект пользователя.
    """
    async with async_session() as session:
        # Обновляем поле tg_id
        stmt = (
            update(User)
            .where(User.id == resident_id)
            .values(tg_id=tg_id)
        )
        await session.execute(stmt)
        await session.commit()
        
        # Получаем обновленного пользователя для возврата
        result = await session.execute(select(User).where(User.id == resident_id))
        return result.scalar_one()


# ==========================================
# РАБОТА С МАШИНАМИ
# ==========================================

async def get_all_machines() -> List[Machine]:
    async with async_session() as session:
        result = await session.execute(select(Machine).order_by(Machine.number_machine))
        return result.scalars().all()


# ==========================================
# ПРОВЕРКА СЛОТОВ
# ==========================================

async def is_slot_free(
    machine_id: int,
    date: datetime,
    duration_minutes: int = 90
) -> bool:
    end_time = date + timedelta(minutes=duration_minutes)

    async with async_session() as session:
        result = await session.execute(
            select(Booking.id).where(
                Booking.inidmachine == machine_id,
                Booking.start_time < end_time,
                Booking.end_time > date,
                Booking.status != 'cancelled'  # Игнорируем отмененные брони
            ).limit(1)
        )
        overlapping = result.scalar_one_or_none()
        return overlapping is None


# ==========================================
# БРОНИРОВАНИЕ И ИСТОРИЯ
# ==========================================

async def create_booking(
    user_id: int,
    machine_id: int,
    start_time: datetime,
    duration_minutes: int = 90
) -> dict:  # Возвращаем словарь вместо объекта Booking
    async with async_session() as session:
        end_time = start_time + timedelta(minutes=duration_minutes)

        if not await is_slot_free(machine_id, start_time, duration_minutes):
            raise ValueError("Слот уже занят")

        booking = Booking(
            inidresidents=user_id,
            inidmachine=machine_id,
            start_time=start_time,
            end_time=end_time,
            status="active"
        )
        session.add(booking)
        await session.commit()
        await session.refresh(booking)
        
        # Получаем информацию о машине
        machine_result = await session.execute(
            select(Machine).where(Machine.id == machine_id)
        )
        machine = machine_result.scalar_one()
        
        return {
            'booking': booking,
            'machine': machine
        }


async def get_user_bookings(tg_id: int) -> List[Booking]:
    async with async_session() as session:
        result = await session.execute(
            select(Booking)
            .join(User, Booking.inidresidents == User.id)
            .where(User.tg_id == tg_id)
            .order_by(Booking.start_time)
        )
        return result.scalars().all()


async def cancel_booking(booking_id: int, tg_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(Booking)
            .join(User, Booking.inidresidents == User.id)
            .where(Booking.id == booking_id, User.tg_id == tg_id)
        )
        booking = result.scalar_one_or_none()

        if booking:
            await session.delete(booking)
            await session.commit()
            return True
        return False
    

# ==========================================
# ЛОГИКА КАЛЕНДАРЯ
# ==========================================

async def get_month_workload(year: int, month: int, machine_type: Optional[str] = None) -> dict:
    """
    Возвращает словарь {день: количество_записей} для указанного месяца 
    и типа машины (опционально).
    Пример: {1: 5, 2: 12, 15: 0}
    """
    async with async_session() as session:
        query = (
            select(
                extract('day', Booking.start_time).cast(Integer).label('day'),
                func.count(Booking.id).label('count')
            )
            .join(Machine, Booking.machine_id == Machine.id) # Добавлено соединение с Machine
            .where(
                extract('year', Booking.start_time) == year,
                extract('month', Booking.start_time) == month,
                Booking.status != 'cancelled' 
            )
            .group_by('day')
        )
        
        # Добавляем условие фильтрации по типу машины, если оно передано
        if machine_type:
            query = query.where(Machine.type_machine == machine_type)
            
        result = await session.execute(query)
        return {row.day: row.count for row in result.all()}

async def get_total_daily_capacity_by_type(machine_type: Optional[str] = None) -> int:
    """
    Считаем МАКСИМАЛЬНОЕ кол-во слотов в день для конкретного типа машины.
    Если тип не указан, считаются все машины.
    """
    async with async_session() as session:
        # Считаем только машины со статусом "Работает"
        conditions = [Machine.status == 'Работает']
        if machine_type:
            conditions.append(Machine.type_machine == machine_type)
        
        query = select(func.count(Machine.id)).where(and_(*conditions))
        result = await session.execute(query)
        active_machines = result.scalar() or 0
    
    # Параметры работы прачечной (8:00 - 23:00) -> 10 слотов по 90 минут
    # Это ваша текущая логика. Предполагаем, что max_capacity = кол-во активных машин.
    return active_machines


async def get_available_machines(start_time: datetime, machine_type: str) -> List[Machine]:
    """Возвращает список свободных машин на указанное время и тип."""
    async with async_session() as session:
        # 1. Получаем все машины нужного типа со статусом "Работает"
        query = select(Machine).where(
            Machine.status == 'Работает',
            Machine.type_machine == machine_type
        )
        result = await session.execute(query)
        working_machines = result.scalars().all()

        if not working_machines:
            return []

        # 2. Асинхронно проверяем, свободна ли каждая машина
        tasks = [is_slot_free(machine.id, start_time) for machine in working_machines]
        availability_results = await asyncio.gather(*tasks)

        # 3. Собираем список только свободных машин
        available_machines = [
            machine for machine, is_free in zip(working_machines, availability_results) if is_free
        ]
        
        return available_machines


async def get_available_slots(
    date: datetime,
    machine_type: Optional[str] = None,
    work_start: int = 8,
    work_end: int = 23,
    slot_duration: int = 90
) -> List[datetime]:
    available = []
    
    current = date.replace(hour=work_start, minute=0, second=0, microsecond=0)
    end_of_day = date.replace(hour=work_end, minute=0, second=0, microsecond=0)

    all_machines = await get_all_machines()

    if machine_type:
        working_machines = [m for m in all_machines if m.status == 'Работает' and m.type_machine == machine_type]
    else:
        working_machines = [m for m in all_machines if m.status == 'Работает']
    
    if not working_machines:
        return []
    
    tasks = []
    while current + timedelta(minutes=slot_duration) <= end_of_day:
        slot_time = current
        for machine in working_machines:
            tasks.append(is_slot_free(machine.id, slot_time, duration_minutes=slot_duration))
        current += timedelta(minutes=slot_duration)
    
    results = await asyncio.gather(*tasks)
    
    current = date.replace(hour=work_start, minute=0, second=0, microsecond=0)
    result_index = 0
    
    while current + timedelta(minutes=slot_duration) <= end_of_day:
        machines_count = len(working_machines)
        slot_results = results[result_index:result_index + machines_count]
        
        if any(slot_results):
            available.append(current)
        
        current += timedelta(minutes=slot_duration)
        result_index += machines_count

    return available
