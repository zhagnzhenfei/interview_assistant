from fastapi import FastAPI
from router import chat_rt, user_rt, account_rt


app = FastAPI()

app.include_router(chat_rt.router)
app.include_router(user_rt.router)
app.include_router(account_rt.router)

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    