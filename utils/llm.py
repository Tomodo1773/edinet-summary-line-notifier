from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import JsonOutputParser

# from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field

from prompt import system_prompt, user_prompt
from schema import ContentData, WatchlistDoc


# chatGPTを使用して財務報告の内容を要約する
def summarize_financial_reports(content_data: ContentData, watchlist_doc: WatchlistDoc):

    # output parserを設定
    class Summary(BaseModel):
        project_status: str = Field(description="事業の状況", max_length=400)
        outlook: str = Field(description="次期の見通し", max_length=400)
        generalize: str = Field(description="総括", max_length=400)

    parser = JsonOutputParser(pydantic_object=Summary)

    template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", user_prompt),
        ],
    )

    prompt = template.partial(format_instructions=parser.get_format_instructions())

    # chatモデルを設定
    # chat = ChatAnthropic(model="claude-3-opus-20240229", max_tokens=4096, temperature=0.7)
    chat = ChatAnthropic(model="claude-3-opus-20240229", max_tokens=4096, temperature=0.7)

    # chainを設定
    chain = prompt | chat | parser
    result = chain.invoke(
        {
            "company_name": watchlist_doc["filerName"],
            "period": content_data["period"],
            "mgmt_issues": content_data["mgmt_issues"],
            "business_risks": content_data["business_risks"],
            "mgmt_analysis": content_data["mgmt_analysis"],
        }
    )
    return result
