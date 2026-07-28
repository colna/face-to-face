"""T1.4 冒烟:包可导入、版本可读。"""
import engine


def test_package_importable() -> None:
    assert engine.__version__ == "0.1.0"
