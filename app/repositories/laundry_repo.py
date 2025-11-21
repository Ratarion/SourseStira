# app/repositories/laundry_repo.py
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import async_session
from app.db.models.user import users as User
from app.db.models.machine import machines as Machine
from app.db.models.booking import booking as Booking
from app.db.models.room import rooms as Room


# === Работа с пользователями ===
async def get_or_create_user(
    tg_id: int,
    id_cards: int,
    room_id: int,
    last_name: str,
    first_name: str,
    patronymic: str | None = None
) -> User:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                tg_id=tg_id,
                idCards=id_cards,
                inIdRoom=room_id,
                last_name=last_name,
                first_name=first_name,
                patronymic=patronymic or ""
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


# === Работа с машинами ===
async def get_all_machines() -> List[Machine]:
    async with async_session() as session:
        result = await session.execute(select(Machine).order_by(Machine.number_machine))
        return result.scalars().all()


# === Проверка свободного времени для машины ===
async def is_slot_free(
    machine_id: int,
    date: datetime,
    duration_minutes: int = 120  # стандартная стирка — 2 часа
) -> bool:
    end_time = date + timedelta(minutes=duration_minutes)

    async with async_session() as session:
        result = await session.execute(
            select(Booking).where(
                Booking.inIdMachine == machine_id,
                Booking.start_time < end_time,
                Booking.end_time > date
            )
        )
        overlapping = result.scalar_one_or_none()
        return overlapping is None


# === Получить все доступные слоты на день ===
async def get_available_slots(
    date: datetime,
    work_start: int = 8,      # с 8:00
    work_end: int = 23,       # до 23:00
    slot_duration: int = 120  # 2 часа
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
                break  # нашли свободную — дальше не проверяем
        current += timedelta(minutes=slot_duration)

    return available


# === Создать бронь ===
async def create_booking(
    user_id: int,
    machine_id: int,
    start_time: datetime,
    duration_minutes: int = 120
) -> Booking:
    async with async_session() as session:
        end_time = start_time + timedelta(minutes=duration_minutes)

        # Если слот уже занят — выбросит исключение (можно обработать выше)
        if not await is_slot_free(machine_id, start_time, duration_minutes):
            raise ValueError("Слот уже занят")

        booking = Booking(
            inIdUser=user_id,
            inIdMachine=machine_id,
            start_time=start_time,
            end_time=end_time
        )
        session.add(booking)
        await session.commit()
        await session.refresh(booking)
        return booking


# === Получить записи пользователя ===
async def get_user_bookings(tg_id: int) -> List[Booking]:
    async with async_session() as session:
        result = await session.execute(
            select(Booking)
            .join(User, Booking.inIdUser == User.id)
            .where(User.tg_id == tg_id)
            .order_by(Booking.start_time)
        )
        return result.scalars().all()


# === Удалить запись ===
async def cancel_booking(booking_id: int, tg_id: int) -> bool:
    async with async_session() as session:
        result = await session.execute(
            select(Booking)
            .join(User, Booking.inIdUser == User.id)
            .where(Booking.id == booking_id, User.tg_id == tg_id)
        )
        booking = result.scalar_one_or_none()

        if booking:
            await session.delete(booking)
            await session.commit()
            return True
        return False