from fastapi import FastAPI
from database import engine,Base
from routers import incident,step,runbooks,incident_histories
import models


Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(incident.router)
app.include_router(step.router)
app.include_router(runbooks.router)
app.include_router(incident_histories.router)

