from curllm_core import CurllmExecutor


def test_human_verify_polish_detection_true():
    ex = CurllmExecutor()
    txt = "Potwierdź, że jesteś człowiekiem."
    assert ex._looks_like_human_verify_text(txt) is True


def test_human_verify_detection_false():
    ex = CurllmExecutor()
    txt = "Welcome to example site"
    assert ex._looks_like_human_verify_text(txt) is False
