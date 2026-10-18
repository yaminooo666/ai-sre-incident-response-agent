from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer, CrossEncoder
import models, schemas



model = SentenceTransformer("all-MiniLM-L6-v2")
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def retrieve_histories(query,histories,top_k):

    if not histories:
        return []

    query_embedding = [model.encode(query)]
    histories_context = []

    for history in histories:
        history_context = []
        history_context.append(history.alert_type if history.alert_type is not None else "")
        history_context.append(history.incident_title if history.incident_title is not None else "")
        history_context.append(history.problem_summary if history.problem_summary is not None else "")

        history_context = "\n".join(history_context)

        histories_context.append(history_context)

    histories_embedding = model.encode(histories_context)

    score = cosine_similarity(query_embedding, histories_embedding)
    score = score[0]

    sum1 = list(zip(histories,score))
    sum1.sort(key= lambda sum1:sum1[1], reverse=True)

    top_sum = sum1[:top_k]
    top_histories = []
    for i in top_sum:
        top_histories.append(i[0])

    return top_histories





def retrieve_runbooks(query,runbooks,top_k):
   
    if not runbooks:
        return []

    query_embedding = [model.encode(query)]
    runbooks_context = []

    for runbook in runbooks:
        runbook_context = []
        runbook_context.append(runbook.alert_type if runbook.alert_type is not None else "")
        runbook_context.append(runbook.title if runbook.title is not None else "")
        runbook_context.append(runbook.content if runbook.content is not None else "")

        runbook_context = "\n".join(runbook_context)

        runbooks_context.append(runbook_context)

    runbooks_embedding = model.encode(runbooks_context)

    score = cosine_similarity(query_embedding, runbooks_embedding)
    score = score[0]

    sum1 = list(zip(runbooks,score))
    sum1.sort(key= lambda sum1:sum1[1], reverse=True)

    top_sum = sum1[:top_k]
    top_runbooks = []
    for i in top_sum:
        top_runbooks.append(i[0])

    return top_runbooks    
        



def rerank_runbooks(query, runbooks,top_k):

    if not runbooks:
        return []
    
    pair = []

    for runbook in runbooks:

        runbook_context = []

        runbook_context.append(runbook.alert_type if runbook.alert_type is not None else "")
        runbook_context.append(runbook.title if runbook.title is not None else "")
        runbook_context.append(runbook.content if runbook.content is not None else "")

        runbook_context = "\n".join(runbook_context)

        pair.append((query,runbook_context))
    
    
    score = reranker.predict(pair)

    ranked_result = list(zip(runbooks,score))

    ranked_result.sort(key = lambda ranked_result:ranked_result[1],reverse = True)

    top_result = ranked_result[:top_k]
    result = []

    for i in top_result:
        result.append(i[0])

    return result






def rerank_histories(query, histories,top_k):

    if not histories:
        return []
    
    pair = []

    for history in histories:

        history_context = []
        history_context.append(history.alert_type if history.alert_type is not None else "")
        history_context.append(history.incident_title if history.incident_title is not None else "")
        history_context.append(history.problem_summary if history.problem_summary is not None else "")

        history_context = "\n".join(history_context)

        pair.append((query,history_context))
    
    score = reranker.predict(pair)

    ranked_result = list(zip(histories,score))

    ranked_result.sort(key = lambda ranked_result:ranked_result[1],reverse = True)

    top_result = ranked_result[:top_k]
    result = []

    for i in top_result:
        result.append(i[0])

    return result
