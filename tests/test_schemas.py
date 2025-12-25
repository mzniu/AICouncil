from src.agents import schemas


def test_plan_schema_minimal():
    sample = {
        "id": "策论家1-plan1",
        "core_idea": "示例思路",
        "steps": ["步骤1","步骤2"],
        "feasibility": {"advantages": ["优点1"], "requirements": ["条件A"]},
        "limitations": ["限制1"]
    }
    p = schemas.PlanSchema(**sample)
    assert p.id == "策论家1-plan1"


def test_auditor_schema_minimal():
    sample = {
        "auditor_id": "监察官1",
        "reviews": [{"plan_id":"策论家1-plan1","issues":["问题"],"suggestions":["建议"],"rating":"合格"}],
        "summary": "总体合格"
    }
    a = schemas.AuditorSchema(**sample)
    assert a.auditor_id == "监察官1"
