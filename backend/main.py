from src.utils.fastset import run

app = run()


@app.get("/")
def read_root():
  return {"msg": "SKM!"}

