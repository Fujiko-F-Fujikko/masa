import inspect

def show_call_stack():
    print("=== Call Stack Trace ===")
    stack = inspect.stack()
    
    for i, frame_info in enumerate(reversed(stack[1:])):  # stack[0] は show_call_stack 自身
        func_name = frame_info.function
        file_name = frame_info.filename
        line_no = frame_info.lineno

        if i == len(stack) - 2:  # 一番直前（= 呼び出し元）
            print(f">>> {func_name}()  ←  {file_name}:{line_no}")  # 強調表示
        else:
            print(f"    {func_name}()  ←  {file_name}:{line_no}")
