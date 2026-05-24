import asyncio
from app.core.database import async_session_maker
from sqlalchemy import select
from app.models.file import File
from app.schemas.file import FileDetailResponse

async def main():
    async with async_session_maker() as session:
        query = select(File).where(File.id == "4c71b944-b38f-4935-95ba-fb4052cbc6c5")
        result = await session.execute(query)
        db_file = result.scalar_one_or_none()
        
        if db_file:
            response = FileDetailResponse.model_validate(db_file)
            print("response json type:", type(response.verification_result_json))
            if response.verification_result_json:
                print("has operator_logs?", "operator_logs" in response.verification_result_json)
        
if __name__ == "__main__":
    asyncio.run(main())
