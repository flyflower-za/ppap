#!/usr/bin/env python3
"""
PDF数字签名校验诊断脚本
用于测试和调试PDF签名识别功能
"""
import sys
import os
sys.path.append('/app')

def test_pyhanko_import():
    """测试pyhanko库导入"""
    print("=== 测试1: pyhanko库导入 ===")
    try:
        from pyhanko.pdf_utils.reader import PdfFileReader
        from pyhanko.sign.validation import async_validate_pdf_signature
        print("✅ pyhanko库导入成功")
        return True
    except Exception as e:
        print(f"❌ pyhanko库导入失败: {e}")
        return False

def test_sig_verifier_import():
    """测试签名验证器导入"""
    print("\n=== 测试2: 签名验证器导入 ===")
    try:
        from app.checkers.sig_verifier import verify_pdf_signatures, PYHANKO_AVAILABLE
        print(f"✅ 签名验证器导入成功")
        print(f"   PYHANKO_AVAILABLE = {PYHANKO_AVAILABLE}")
        return True
    except Exception as e:
        print(f"❌ 签名验证器导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_signature_operator():
    """测试签名操作符"""
    print("\n=== 测试3: 签名操作符导入 ===")
    try:
        from app.engine.operators.signature_operator import SignatureOperator
        op = SignatureOperator()
        print(f"✅ 签名操作符导入成功")
        print(f"   操作符名称: {op.name}")
        print(f"   提供的数据: {op.provides}")
        print(f"   需要的数据: {op.requires}")
        return True
    except Exception as e:
        print(f"❌ 签名操作符导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_engine_registration():
    """测试引擎中的签名操作符注册"""
    print("\n=== 测试4: 引擎注册检查 ===")
    try:
        from app.engine.core import VerificationEngine
        engine = VerificationEngine()
        print(f"✅ 引擎初始化成功")
        print(f"   可用操作符: {list(engine._available_operators.keys())}")

        if "SignatureVerifier" in engine._available_operators:
            print(f"✅ SignatureVerifier已注册")
            return True
        else:
            print(f"❌ SignatureVerifier未注册")
            return False
    except Exception as e:
        print(f"❌ 引擎检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_requirements_file():
    """检查requirements.txt中的依赖"""
    print("\n=== 测试5: 依赖检查 ===")
    try:
        with open('/app/requirements.txt', 'r') as f:
            content = f.read()
            has_pyhanko = 'pyhanko' in content.lower()
            has_cryptography = 'cryptography' in content.lower()
            print(f"   pyhanko: {'✅' if has_pyhanko else '❌'}")
            print(f"   cryptography: {'✅' if has_cryptography else '❌'}")
            return has_pyhanko and has_cryptography
    except Exception as e:
        print(f"❌ 依赖检查失败: {e}")
        return False

def main():
    print("🔍 PDF数字签名校验诊断工具")
    print("=" * 50)

    results = []
    results.append(("pyhanko库导入", test_pyhanko_import()))
    results.append(("签名验证器导入", test_sig_verifier_import()))
    results.append(("签名操作符导入", test_signature_operator()))
    results.append(("引擎注册检查", test_engine_registration()))
    results.append(("依赖文件检查", test_requirements_file()))

    print("\n" + "=" * 50)
    print("📊 诊断结果汇总:")
    print("=" * 50)

    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name:20s} {status}")

    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)

    print(f"\n总计: {total_passed}/{total_tests} 测试通过")

    if total_passed == total_tests:
        print("🎉 所有测试通过！PDF签名校验功能应该正常工作。")
        return 0
    else:
        print("⚠️  部分测试失败，需要进一步调查。")
        return 1

if __name__ == "__main__":
    sys.exit(main())