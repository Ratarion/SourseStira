import asyncio
from datetime import datetime, timedelta
from sqlalchemy import Integer
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


async def get_available_slots(
    date: datetime,
    work_start: int = 8,      # с 8:00
    work_end: int = 23,       # до 23:00
    slot_duration: int = 90   # стирка — 1 час 30 минут
) -> List[datetime]:
    """Возвращает список доступных начал слотов на указанную дату"""
    available = []
    
    current = date.replace(hour=work_start, minute=0, second=0, microsecond=0)
    end_of_day = date.replace(hour=work_end, minute=0, second=0, microsecond=0)

    # Получаем все машины одним запросом
    machines = await get_all_machines()
    
    # Создаем задачи для проверки слотов
    tasks = []
    while current + timedelta(minutes=slot_duration) <= end_of_day:
        slot_time = current
        # Проверяем для каждой машины
        for machine in machines:
            tasks.append(is_slot_free(machine.id, slot_time, slot_duration))
        current += timedelta(minutes=slot_duration)
    
    # Выполняем все проверки параллельно
    results = await asyncio.gather(*tasks)
    
    # Обрабатываем результаты
    current = date.replace(hour=work_start, minute=0, second=0, microsecond=0)
    result_index = 0
    
    while current + timedelta(minutes=slot_duration) <= end_of_day:
        # Проверяем, есть ли хотя бы одна свободная машина в этом слоте
        machines_count = len(machines)
        slot_results = results[result_index:result_index + machines_count]
        
        if any(slot_results):
            available.append(current)
        
        current += timedelta(minutes=slot_duration)
        result_index += machines_count

    return available


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

async def get_month_workload(year: int, month: int) -> dict:
    """
    Возвращает словарь {день: количество_записей} для указанного месяца.
    Пример: {1: 5, 2: 12, 15: 0}
    """
    async with async_session() as session:
        query = (
            select(
                extract('day', Booking.start_time).cast(Integer).label('day'),
                func.count(Booking.id).label('count')
            )
            .where(
                extract('year', Booking.start_time) == year,
                extract('month', Booking.start_time) == month,
                Booking.status != 'cancelled' 
            )
            .group_by('day')
        )
        result = await session.execute(query)
        return {row.day: row.count for row in result.all()}

async def get_total_daily_capacity() -> int:
    """
    Считаем МАКСИМАЛЬНОЕ кол-во слотов в день.
    """
    async with async_session() as session:
        # Считаем только рабочие машины (не broken)
        # Если статус 'free' или 'busy' — машина рабочая. Если 'broken' — нет.
        # В вашем machine.py default='free'. Предположим, что все, кроме 'broken', рабочие.
        query = select(func.count(Machine.id)).where(Machine.status != 'broken')
        result = await session.execute(query)
        active_machines = result.scalar() or 0
    
    # Параметры работы прачечной
    # 8:00 - 23:00 = 15 часов.
    # Слот 1.5 часа (90 мин).
    # 15 / 1.5 = 10 слотов на одну машину.
    SLOTS_PER_MACHINE = 10
    
    return active_machines * SLOTS_PER_MACHINE