import pytest
import aiohttp
import asyncio

async def register_user(session, url, data):
    async with session.post(url, json=data) as response:
        return await response.json()

@pytest.mark.asyncio
async def test_concurrency_userRegistration():
    url = "http://localhost:5000/api/v1/register"
    username = "testingUseragain7"
    password = "password123"
    data = {"username": username, "password": password}

    async with aiohttp.ClientSession() as session:
        #Launch 10 concurrent requests to register the same user
        tasks = [register_user(session, url, data) for _ in range(10)]
        responses = await asyncio.gather(*tasks)

    for response in responses:
        print(response)

    success_responses = [response for response in responses if "user_id" in response]
    error_responses = [response for response in responses if "error" in response]

    #Only 1 user should succeed
    assert len(success_responses) == 1, f"Expected 1 successful registration, but got {len(success_responses)}."

    #Other responses should fail
    assert len(error_responses) == 9, f"Expected 9 error responses, but got {len(error_responses)}."
    for response in error_responses:
        error_message = response.get("error", "")
        assert "Username already exists" in error_message, f"Unexpected error message: {error_message}"

