def get_recommendation(risk_level: str) -> str:
    recommendations = {
        "Low": "Maintain good health practices and monitor symptoms.",
        "Moderate": "Visit a healthcare facility for sputum smear microscopy.",
        "High": "Urgent evaluation required. Perform GeneXpert test and chest X-ray.",
        "Emergency": "Emergency referral required immediately for GeneXpert test, chest X-ray, and culture/drug susceptibility testing."
    }
    return recommendations.get(risk_level, "No recommendation available.")


def get_recommendation_key(risk_level: str) -> str:
    mapping = {
        "Low": "recommendation.low",
        "Moderate": "recommendation.moderate",
        "High": "recommendation.high",
        "Emergency": "recommendation.emergency"
    }
    return mapping.get(risk_level, "recommendation.low")


def get_test_recommendation(risk_level: str) -> str:
    test_map = {
        "Low": "No immediate lab test recommended. Monitor symptoms and return if symptoms persist.",
        "Moderate": "Recommended test: Sputum smear microscopy.",
        "High": "Recommended tests: GeneXpert (NAAT) and Chest X-ray.",
        "Emergency": "Recommended urgent tests: GeneXpert (NAAT), Chest X-ray, and TB culture/drug susceptibility testing."
    }
    return test_map.get(risk_level, "No test recommendation available.")


def get_test_recommendation_key(risk_level: str) -> str:
    mapping = {
        "Low": "test.low",
        "Moderate": "test.moderate",
        "High": "test.high",
        "Emergency": "test.emergency"
    }
    return mapping.get(risk_level, "test.low")