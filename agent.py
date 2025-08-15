# Langchain Agent xử dụng các tools
from langchain.agents import initialize_agent, Tool
from langchain.chat_models import ChatOpenAI
from facebook_tools import get_page_info, get_latest_posts

tools = [
    Tool.from_function(func=get_page_info, name="GetPageInfo", description="Lấy thông tin Fanpage"),
    Tool.from_function(func=get_latest_posts, name="GetLatestPosts", description="Lấy bài viết mới từ Fanpage"),
]

llm = ChatOpenAI(temperature=0)
agent = initialize_agent(tools, llm, agent="chat-zero-shot-react-description", verbose=True)
