import pandas as pd
from nicegui import ui, app
from shell import apply_theme, require_login, render_sidebar, tt_card, page_title
from data_layer import (
    get_users_with_status, delete_user, update_user_password, register_user,
    get_all_usernames, get_db_connection, load_user_db,
)


@ui.page('/users')
def users_page():
    apply_theme()
    user = require_login()
    if not user:
        return
    render_sidebar(user, '/users')
    is_admin = user.strip().lower() == 'admin'

    with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
        page_title('/users')

        # --- Change Password: available to every logged-in user ---
        with tt_card('🔑 Change Password'):
            with ui.grid(columns=3).classes('w-full gap-4'):
                cp_old = ui.input('Current Password', password=True)
                cp_new = ui.input('New Password', password=True)
                cp_confirm = ui.input('Confirm New Password', password=True)

            def do_change_password():
                if not cp_old.value or not cp_new.value or not cp_confirm.value:
                    ui.notify('⚠️ Fill in all three fields.', type='warning')
                elif cp_new.value != cp_confirm.value:
                    ui.notify('❌ New passwords do not match!', type='negative')
                else:
                    success, msg = update_user_password(user, cp_old.value, cp_new.value)
                    if success:
                        ui.notify(msg, type='positive')
                        cp_old.set_value(''); cp_new.set_value(''); cp_confirm.set_value('')
                    else:
                        ui.notify(msg, type='negative')

            ui.button('🔄 Update Password', on_click=do_change_password, color=None).classes('mt-2 tt-goldbtn')

        # --- Clear My Roster: available to every logged-in user, with confirmation ---
        with tt_card('🗑️ Clear My Roster'):
            ui.label('Permanently deletes every player in your own roster. This cannot be undone.').classes('text-sm text-gray-400')
            confirm_clear_cb = ui.checkbox('I understand this permanently deletes all my players')

            def do_clear_roster():
                if not confirm_clear_cb.value:
                    ui.notify('⚠️ Check the confirmation box first.', type='warning')
                    return
                conn = get_db_connection()
                conn.cursor().execute('DELETE FROM skills_data WHERE LOWER(username) = LOWER(?);', (user,))
                conn.commit()
                conn.close()
                load_user_db.clear()
                ui.notify('✅ Your roster has been cleared.', type='positive')
                confirm_clear_cb.set_value(False)

            ui.button('🗑️ Clear My Roster', on_click=do_clear_roster).classes('mt-2')

        if not is_admin:
            return

        # --- Admin-only: user overview, create account, delete account ---
        us = get_users_with_status()

        with tt_card('📋 System User Accounts (Admin)'):
            rows = [{
                'Status': '🟢 Online now' if u['online'] else '⚪ Offline',
                'Username': u['username'],
                'Last Login': pd.Timestamp(u['last_login']).strftime('%Y-%m-%d %H:%M UTC') if u['last_login'] else 'Never',
            } for u in us]
            ui.table(columns=[{'name': c, 'label': c, 'field': c} for c in ['Status', 'Username', 'Last Login']], rows=rows).classes('w-full')
            with ui.row().classes('gap-8 mt-4'):
                ui.label(f'Total Registered Users: {len(us)}')
                ui.label(f"Currently Online: {sum(1 for u in us if u['online'])}")

        with tt_card('➕ Create User Account (Admin)'):
            with ui.grid(columns=2).classes('w-full gap-4'):
                new_user_input = ui.input('New Username')
                new_pass_input = ui.input('Password for New User', password=True)

            def do_create_user():
                if not new_user_input.value or not new_pass_input.value:
                    ui.notify('⚠️ Please fill in both fields.', type='warning')
                    return
                if register_user(new_user_input.value, new_pass_input.value):
                    ui.notify(f'✅ Account "{new_user_input.value}" created!', type='positive')
                    new_user_input.set_value(''); new_pass_input.set_value('')
                    get_users_with_status.clear()
                    ui.navigate.to('/users')
                else:
                    ui.notify('❌ Username already exists!', type='negative')

            ui.button('➕ Create User Account', on_click=do_create_user).classes('mt-2')

        with tt_card('🗑️ Remove User Account (Admin)'):
            usernames = get_all_usernames()
            del_select = ui.select(usernames, label='Select User to Delete', value=(usernames[0] if usernames else None)).classes('w-64')
            confirm_cb = ui.checkbox('I understand this permanently deletes this account and roster data')

            def do_delete():
                sel = del_select.value
                if not sel:
                    return
                if sel.lower() == user.lower():
                    ui.notify('❌ You cannot delete your currently active logged-in account!', type='negative')
                elif sel.lower() == 'admin':
                    ui.notify('❌ The primary "admin" system account cannot be deleted!', type='negative')
                elif not confirm_cb.value:
                    ui.notify('⚠️ Please check the confirmation box first.', type='warning')
                else:
                    success, msg = delete_user(sel)
                    if success:
                        get_users_with_status.clear()
                        ui.notify(msg, type='positive')
                        ui.navigate.to('/users')
                    else:
                        ui.notify(msg, type='negative')

            ui.button('🗑️ Delete User Account', on_click=do_delete).classes('mt-2')