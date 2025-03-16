from services.auth import register_user, authenticate
from utils.database import init_db

if __name__ == "__main__":
    # 初始化数据库
    init_db()
    
    # 注册新用户
    try:
        register_user("user2", "abcd1234")
        print("用户注册成功")
    except Exception as e:
        print(f"注册失败: {e}")
    
    # 认证用户
    try:
        token = authenticate("user2", "abcd1234")
        print(f"认证成功，token: {token}")
    except Exception as e:
        print(f"认证失败: {e}")