import models
import constans as c
from tools.registry import TOOLS








@pytest.fixture
def db(tmp_path):

    test_url = f"sqlite:///{tmp_path / 'test.db'}"

    test_engine = create_engine(
        test_url,
        connect_args={"check_same_thread": False}
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )

    Base.metadata.create_all(bind=test_engine)

    with TestingSessionLocal() as session:
        yield session

    test_engine.dispose()



case = {
        "incident" : {
            "title": "...",
            "service_name": "...",
            "alert_type": "...",
            "severity": 2,
            "description": "..."
        },

        "expected" : {
            "allowed_tools": [...],
            "forbidden_tools": [...],
            "must_require_approval_for": [...],
            "must_verify_after_restart": True,
            "must_not_resolve_if_abnormal": True,
            "must_not_resolve_after_re_evaluate": True
        }
}


def evaluate_runner(db,case):
    temp = case["incident"]
    expected = case["expected"]
    
    incident = models.Incident(
        title=temp["title"],
        service_name=temp["service_name"],
        alert_type=temp["alert_type"],
        severity=temp["severity"],
        description=temp["description"],
        status=c.INCIDENT_STATUS_EXECUTING
    )
    db.add(incident)
    db.commit()

    run_agent(db,incident)

    used_tools = collect_used_tools(incident)
    for i in range(len(used_tools)):
        assert used_tools[i] in TOOLS
        assert used_tools[i] in expected["allowed_tools"]
        assert used_tools[i] not in expected["forbidden_tools"]

    steps = require_approval_for(incident,expected["must_require_approval_for"])
    for step in steps:
        assert step.approval_required == True
    


    
    

def collect_used_tools(incident):
    plans = incident.plans
    l = len(plans)-1
    plan = plans[l]
    steps= []

    for step in plan.steps:
        steps.append(step.action_type)
    return steps


def restart_verification(incident):
    plans = incident.plans
    l = len(plans)-1
    steps= plans[l].steps
    result = []
    i = 0

    while i+1<=len(steps)-1:
        if steps[i].action_type == c.ACTION_RESTART_SERVICE:
            result.append(steps[i+1])
        i+=1 

    if steps[i].action_type == c.ACTION_RESTART_SERVICE:
        return False
    else:
        return result


def require_approval_for(incident,approve_steps):
    plans = incident.plans
    l = len(plans)-1
    steps= plans[l].steps
    result = []
    
    for step in steps:
        if step.action_type in approve_steps:
            result.append(step)
    return result