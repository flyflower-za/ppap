"""
签发机构嗅探算法工作原理演示
"""

def demonstrate_algorithm():
    print("=" * 60)
    print("🧠 签发机构嗅探算法工作原理演示")
    print("=" * 60)

    # 机构特征词典
    institution_patterns = {
        "CTI": ["华测", "华测检测", "CTI", "centre testing international"],
        "SGS": ["SGS", "sgs", "通标标准", "通标"],
        "TUV": ["TUV", "tuv", "莱茵", "TÜV"],
    }

    test_cases = [
        "华测检测认证集团股份有限公司，质量检测报告CTI-2024",
        "SGS通标标准技术服务有限公司，编号SGS-2024-123",
        "TÜV莱茵认证，产品符合标准"
    ]

    for i, doc_content in enumerate(test_cases, 1):
        print(f"\n📄 测试案例 {i}:")
        print(f"   文档内容: {doc_content}")
        print(f"   处理过程:")

        best_match = {"institution": "UNKNOWN", "confidence": 0.0, "matches": 0}

        for institution, patterns in institution_patterns.items():
            match_count = 0
            matched_patterns = []

            for pattern in patterns:
                if pattern.lower() in doc_content.lower():
                    match_count += 1
                    matched_patterns.append(pattern)

            if match_count > 0:
                # 置信度计算
                base_confidence = 0.6 + (match_count * 0.15)
                if len(doc_content) > 30:  # 演示用，降低阈值
                    base_confidence += 0.1
                confidence = min(base_confidence, 0.95)

                print(f"   ├─ 识别机构: {institution}")
                print(f"   │  匹配特征: {matched_patterns}")
                print(f"   │  匹配数量: {match_count}")
                print(f"   │  置信度计算: 0.6 + {match_count}×0.15 + 0.1 = {confidence:.2f}")

                if match_count > best_match["matches"]:
                    best_match = {
                        "institution": institution,
                        "confidence": confidence,
                        "matches": match_count
                    }

        print(f"   ✅ 最终结果: {best_match['institution']}, 置信度: {best_match['confidence']:.2f}")

    print("\n" + "=" * 60)
    print("🔑 算法要点:")
    print("   1. 模式匹配: 在文档中查找机构特征词")
    print("   2. 评分机制: 匹配越多，置信度越高")
    print("   3. 内容加成: 长文档获得额外置信度")
    print("   4. 最佳选择: 选择匹配数量最多的结果")
    print("=" * 60)

if __name__ == "__main__":
    demonstrate_algorithm()