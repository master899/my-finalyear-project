def evaluate_risk(data: dict) -> str:
    if data.get("coughing_blood"):
        return "Emergency"

    if data.get("cough_duration") and data.get("night_sweats") and data.get("weight_loss"):
        return "High"

    if data.get("cough_duration") and (
        data.get("night_sweats") or data.get("weight_loss") or data.get("fever")
    ):
        return "Moderate"

    return "Low"
