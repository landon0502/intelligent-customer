from app.utils.response import success, error


def test_success_returns_code_zero():
    result = success(data={"key": "value"})
    assert result["code"] == 0
    assert result["message"] == "success"
    assert result["data"] == {"key": "value"}


def test_success_with_custom_message():
    result = success(data=None, message="created")
    assert result["code"] == 0
    assert result["message"] == "created"


def test_error_returns_given_code():
    result = error(code=40000, message="参数错误")
    assert result["code"] == 40000
    assert result["message"] == "参数错误"
    assert result["data"] is None
