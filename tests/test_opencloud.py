from factory.opencloud import LuauTaskRef


def test_task_ref_is_immutable():
    ref = LuauTaskRef("session", "task")
    assert ref.session_id == "session"
    assert ref.task_id == "task"
