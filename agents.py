import asyncio
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor

from prompts import (
    SCRAPPER_SYSTEM_MESSAGE, 
    SEARCH_SYSTEM_MESSAGE, 
    REPORT_SYSTEM_MESSAGE, 
    SUPERVISOR_SYSTEM_AGENT
)
from tools import web_scraper, web_search

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.2
)

async def run_graph():
    
    scrapper_agent = create_react_agent(
        model=llm,
        tools=[web_scraper],
        prompt=SCRAPPER_SYSTEM_MESSAGE,
        name="scrapper_agent"
    )

    research_agent = create_react_agent(
        model=llm,
        tools=[web_search],
        prompt=SEARCH_SYSTEM_MESSAGE,
        name="researcher_agent"
    )

    reporter_agent = create_react_agent(
        model=llm,
        tools=[],
        prompt=REPORT_SYSTEM_MESSAGE,
        name="reporter_agent"
    )

    supervisor = create_supervisor(
        model=llm,
        agents=[research_agent, scrapper_agent, reporter_agent],
        prompt=SUPERVISOR_SYSTEM_AGENT,
        add_handoff_back_messages=True,
        output_mode="full_history",
    ).compile()
    
    return supervisor

# Run the graph
graph = asyncio.run(run_graph())