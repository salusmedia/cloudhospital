from py_common.desensitize import mask_id_card, mask_name, mask_phone


def test_mask_phone():
    assert mask_phone("13812348000") == "138****8000"
    assert mask_phone("123") == "***"


def test_mask_id_card():
    assert mask_id_card("110101199001011234") == "110101********1234"
    assert mask_id_card("123") == "***"


def test_mask_name():
    assert mask_name("张三") == "张*"
    assert mask_name("张三丰") == "张*丰"
    assert mask_name("欧阳娜娜") == "欧**娜"
    assert mask_name("王") == "王"
