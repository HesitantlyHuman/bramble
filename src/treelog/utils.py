def stringify_function_call(func, args: list, kwargs: dict):
    function_call = f"{func.__name__}("
    for arg in args:
        try:
            function_call += f"{arg},\n"
        except Exception:
            function_call += f"`ERROR`,\n"
    for key, value in kwargs.items():
        try:
            function_call += f"{key}={value},\n"
        except Exception:
            function_call += f"{key}=`ERROR`,\n"
    function_call += ")"
    return function_call
