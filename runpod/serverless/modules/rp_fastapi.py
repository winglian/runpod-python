''' Used to launch the FastAPI web server when worker is running in API mode. '''

import os

import uvicorn
from fastapi import FastAPI, APIRouter
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

import runpod
from .job import run_job
from .worker_state import set_job_id
from .heartbeat import HeartbeatSender

RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID", None)

DESCRIPTION = """
This API server is provided as a method of testing and debugging your worker locally.
Additionally, you can use this to test code that will be making requests to your worker.

### Endpoints

The URLs provided are named to match the endpoints that you will be provided when running on RunPod.

---

*Note: When running your worker on the RunPod platform, this API server will not be used.*
"""

try:
    RUNPOD_VERSION = runpod.__version__
except AttributeError:
    RUNPOD_VERSION = "0.0.0"

heartbeat = HeartbeatSender()


class Job(BaseModel):
    ''' Represents a job. '''
    id: str
    input: dict | list | str | int | float | bool


class TestJob(BaseModel):
    ''' Represents a test job.
    input can be any type of data.
    '''
    id: str = "test_job"
    input: dict | list | str | int | float | bool


class WorkerAPI:
    ''' Used to launch the FastAPI web server when the worker is running in API mode. '''

    def __init__(self, handler=None):
        '''
        Initializes the WorkerAPI class.
        1. Starts the heartbeat thread.
        2. Initializes the FastAPI web server.
        3. Sets the handler for processing jobs.
        '''
        # Start the heartbeat thread.
        heartbeat.start_ping()

        # Set the handler for processing jobs.
        self.config = {"handler": handler}

        # Initialize the FastAPI web server.
        self.rp_app = FastAPI(
            title="RunPod | Test Worker | API",
            description=DESCRIPTION,
            version=RUNPOD_VERSION,
        )

        # Create an APIRouter and add the route for processing jobs.
        api_router = APIRouter()

        if RUNPOD_ENDPOINT_ID:
            api_router.add_api_route(f"/{RUNPOD_ENDPOINT_ID}/realtime", self.run, methods=["POST"])

        api_router.add_api_route("/runsync", self.test_run, methods=["POST"])

        # Include the APIRouter in the FastAPI application.
        self.rp_app.include_router(api_router)

    def start_uvicorn(self, api_host='localhost', api_port=8000, api_concurrency=1):
        '''
        Starts the Uvicorn server.
        '''
        uvicorn.run(
            self.rp_app, host=api_host,
            port=int(api_port), workers=int(api_concurrency),
            log_level="info",
            access_log=False
        )

    async def run(self, job: Job):
        '''
        Performs model inference on the input data using the provided handler.
        If handler is not provided, returns an error message.
        '''
        if self.config["handler"] is None:
            return {"error": "Handler not provided"}

        # Set the current job ID.
        set_job_id(job.id)

        # Process the job using the provided handler.
        job_results = run_job(self.config["handler"], job.__dict__)

        # Reset the job ID.
        set_job_id(None)

        # Return the results of the job processing.
        return jsonable_encoder(job_results)

    async def test_run(self, job: TestJob):
        '''
        Performs model inference on the input data using the provided handler.
        '''
        if self.config["handler"] is None:
            return {"error": "Handler not provided"}

        # Set the current job ID.
        set_job_id(job.id)

        job_results = run_job(self.config["handler"], job.__dict__)

        job_results["id"] = job.id

        # Reset the job ID.
        set_job_id(None)

        return jsonable_encoder(job_results)
