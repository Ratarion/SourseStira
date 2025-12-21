# --- Китайский СЛОВАРЬ ЛОКАЛИЗАЦИИ ---
CNtexts = {
    "CN": {
        "hello_user": "你好, {name}! 请选择一个操作:",
        "welcome_lang_choice": "Здравствуйте, выберите язык\nHello, choose a language\n你好, 选择语言",
        "record_laundry": "预订洗衣",
        "report_in_admin": "报告问题",
        "show_records": "查看我的预订",
        "cancel_record": "取消预订",
        "exit": "退出",
        "back": "返回",
        "machine_type": "洗衣机",
        "select_machine_type": "选择机器类型",
        "for_wash": "用于洗涤",
        "for_dry": "用于干燥",

        # --- 预订 / 日历 ---
        "record_start": "选择日期",
        "past_date_error": "该日期已过。请选择其他日期。",

        # ⚠️ 已存在（保留）
        "time_prompt": "选择 {date} 的时间:",

        # ✅ 新增 ключи（必须）
        "select_time_prompt": "选择 {date} 的时间:",
        "select_date_prompt": "请选择日期",
        "day_fully_booked": "该日期已被全部预订。",
        "no_slots_available": "所选日期没有可用的时间段。",
        "no_available_slots_alert": "此时间没有可用的机器。",

        "slots_none": "{date} 无可用时段",

        "machine_type_wash": "洗衣",
        "machine": "机器",
        "show_records_title": "您的预约：",
        "no_user_bookings": "您当前没有预约。",
        "machine_type_dry": "干燥",
        "no_active_machines_type": "没有选定类型的可用机器！",
        "no_active_machines": "当前没有可用的机器。",
        "cancel_prompt": "选择要取消的预订。\n点击按钮释放时段：",
        "cancel_confirm_success": "✅ 预订已成功取消。\n已向其他住户发送空位通知。",
        "cancel_error": "❌ 取消失败或预订已失效。",
        "slot_freed_notification": "🔔 <b>有空位了！</b>\n\n📅 日期: {date}\n⏰ 时间: {time}\n🧺 {m_type} №{m_num}\n\n快去预订吧！",

        "machines_none": "抱歉！此时间所有机器都已被占用。",
        "machine_prompt": "选择 {datetime} 的洗衣机:",
        "booking_success": "预订成功!\n洗衣机 №{machine_num}\n{start} – {end}",
        "booking_error": "该时段已被其他用户预订!",
        "slot_just_taken": "该时间段刚刚被占用，请选择其他时间。",

        # --- 认证 ---
        "none_user": "系统中未找到数据。请联系管理员。",
        "reg_id_error": "请只输入数字。",
        "other_tg_id": "该用户已使用其他账户注册。",
        "seek_cards": "未找到该姓名的用户。请输入学生证号码（仅数字）。",
        "auth": "请输入您的全名（姓、名、父名）以进行授权：",
        "write_FIO": "请输入您的全名（至少两个词）。",
    }
}
