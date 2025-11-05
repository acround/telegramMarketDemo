# state.py
# Общее состояние (только пользовательская часть)

# Корзины пользователей: {user_id: {product_id: qty}}
carts: dict[int, dict[int, int]] = {}

# Доступ к админ-панели (после "demo admin")
demo_admin_access: set[int] = set()

# FSM профиля (только для текущего пользователя): {user_id: {"action": "edit_phone"|"edit_address"}}
user_fsm: dict[int, dict] = {}
