from langfuse import Langfuse

langfuse = Langfuse()
# def fetch_prompts_on_startup():
#     langfuse.get_prompt("rfp-project-tickets")
#     langfuse.get_prompt("rfp-project-summary")
#     langfuse.get_prompt("highlight-generation")

#     langfuse.get_prompt("tools-choice")
#     langfuse.get_prompt("project-chat-prompt")
#     langfuse.get_prompt("ticket-answer-generation")

RFP_PROJECT_TICKETS_PROMPT = langfuse.get_prompt("rfp-project-tickets")
RFP_PROJECT_SUMMARY_PROMPT = langfuse.get_prompt("rfp-project-summary")
HIGHLIGHT_GENERATION_PROMPT = langfuse.get_prompt("highlight-generation")
TOOLS_CHOICE_PROMPT = langfuse.get_prompt("tools-choice")
PROJECT_CHAT_PROMPT = langfuse.get_prompt("project-chat-prompt")
TICKET_ANSWER_GENERATION_PROMPT = langfuse.get_prompt("ticket-answer-generation")
CURATED_QA_PROMPT =  """You are a professional assistant that helps vendors respond to RFPs by extracting valuable historical question-answer pairs from existing RFP documents.
Focus on extracting:

Explicit questions asked in the document and their corresponding answers.

Implicit Q&A where the text describes a requirement and the vendor's response or approach can be inferred.

Extract reusable question-answer pairs that would help a company draft new responses to similar RFPs in the future.

## Instructions
For the provided page, extract relevant question-answer (Q&A) pairs if any exist. Each Q&A should be:

- Concise and standalone.
- Actionable or informative for RFP drafting.
- Preferably based on clearly identifiable information from the text (not invented).
"""