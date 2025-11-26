# app/repositories/laundry_repo.py
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, update, delete, and_, func
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
    duration_minutes: int = 90  # стирка — 1 час 30 минут
) -> bool:
    end_time = date + timedelta(minutes=duration_minutes)

    async with async_session() as session:
        result = await session.execute(
            select(Booking).where(
                Booking.inidmachine == machine_id,
                Booking.start_time < end_time,
                Booking.end_time > date
            )
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

    machines = await get_all_machines()

    while current + timedelta(minutes=slot_duration) <= end_of_day:
        # Если хотя бы одна машина свободна — слот доступен
        for machine in machines:
            if await is_slot_free(machine.id, current, slot_duration):
                available.append(current)
                break  # нашли свободную — дальше не проверяем (для списка времени)
        current += timedelta(minutes=slot_duration)

    return available


# ==========================================
# БРОНИРОВАНИЕ И ИСТОРИЯ
# ==========================================

async def create_booking(
    user_id: int,
    machine_id: int,
    start_time: datetime,
    duration_minutes: int = 120
) -> Booking:
    async with async_session() as session:
        end_time = start_time + timedelta(minutes=duration_minutes)

        # Если слот уже занят — выбросит исключение
        if not await is_slot_free(machine_id, start_time, duration_minutes):
            raise ValueError("Слот уже занят")

        booking = Booking(
            inidresidents=user_id,
            inidmachine=machine_id,
            start_time=start_time,
            end_time=end_time,
            status="active" # Добавил статус явно, если поле nullable=True
        )
        session.add(booking)
        await session.commit()
        await session.refresh(booking)
        return booking


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
        return Falseы