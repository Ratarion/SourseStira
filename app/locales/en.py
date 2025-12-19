# --- СЛОВАРЬ ЛОКАЛИЗАЦИИ ---
ENtexts = {
    "ENG": {
        "hello_user": "Hello, {name}! Choose an action:",
        "welcome_lang_choice": "Hello, choose a language",
        "record_laundry": "Book a wash",
        "report_in_admin": "Report a problem",
        "show_records": "Show my bookings",
        "cancel_record": "Cancel booking",
        "exit": "Exit",
        "back": "Back",
        "machine_type": "Machine",
        "select_machine_type": "Select machine type",
        "for_wash": "for washing",
        "for_dry": "for drying",

        # Booking / calendar
        "record_start": "Select a date (function under development)",
        "past_date_error": "This day has already passed. Please choose another date.",
        # legacy key (kept)
        "time_prompt": "Select a time for {date}:",
        # new key used in code
        "select_time_prompt": "Select a time for {date}:",
        "select_date_prompt": "Please select a date",
        "day_fully_booked": "This date is fully booked.",
        "no_slots_available": "No slots available on the selected date.",
        "no_available_slots_alert": "No available machines at this time.",
        "slots_none": "No free slots available on {date}",

        "machine_type_wash": "Washing",
        "machine_type_dry": "Drying",
        "no_active_machines_type": "No active machines of the selected type!",
        # key used when overall capacity == 0 in your handler
        "no_active_machines": "No active machines available right now.",
        # Title for section menu when returning from errors
        "section_menu_title": "Main menu",

        "machines_none": "Oops! All machines are busy at this time.",
        "machine_prompt": "Select a washing machine for {datetime}:",
        "booking_success": "Booking created!\nMachine №{machine_num}\n{start} – {end}",
        "booking_error": "The slot is already taken by another user!",
        "slot_just_taken": "Sorry — someone just took this slot. Try another one.",

        # Authentication
        "none_user": "No data was found in the system. Please contact the administrator.",
        "reg_id_error": "Please enter only numbers.",
        "other_tg_id": "This user is already registered with another account.",
        "seek_cards": "No user with this name was found. Enter your student ID number (numbers only)",
        "auth": "Enter your full name (surname, first name, and patronymic) to log in",
        "write_FIO": "Please enter your full name (at least 2 words).",
    }
}
