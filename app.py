from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

# Technician data
technicians = [
    {
        "id": 1,
        "name": "Ravi Kumar",
        "location": "Coimbatore",
        "skills": ["Plumbing", "Cleaning"],
        "rating": 4.8,
        "available": True
    },
    {
        "id": 2,
        "name": "Suresh Babu",
        "location": "Chennai",
        "skills": ["Electrical", "AC Repair"],
        "rating": 4.6,
        "available": True
    },
    {
        "id": 3,
        "name": "Anitha R",
        "location": "Coimbatore",
        "skills": ["AC Repair", "Appliance Repair"],
        "rating": 4.9,
        "available": True
    }
]


@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/script.js")
def script():
    return send_from_directory(".", "script.js")


@app.route("/create-request", methods=["POST"])
def create_request():
    data = request.json

    customer = data.get("customer")
    location = data.get("location")
    category = data.get("category")
    description = data.get("description")

    # Find available technicians with the required skill
    candidates = [
        t for t in technicians
        if t["available"] and category in t["skills"]
    ]

    # Prefer same location, then higher rating
    candidates.sort(
        key=lambda t: (
            t["location"].lower() != location.lower(),
            -t["rating"]
        )
    )

    if not candidates:
        return jsonify({
            "success": False,
            "status": "Pending",
            "technician": None,
            "message": "No technician available"
        })

    technician = candidates[0]
    technician["available"] = False

    return jsonify({
        "success": True,
        "status": "Assigned",
        "technician": technician["name"],
        "customer": customer,
        "category": category,
        "description": description
    })


if __name__ == "__main__":
    app.run(debug=True)