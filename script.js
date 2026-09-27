document.addEventListener("DOMContentLoaded", () => {

    const button = document.querySelector(
        'button[onclick="createRequest()"]'
    );

    if (!button) {
        console.log("Create request button not found");
        return;
    }

    button.addEventListener("click", async () => {

        const customer =
            document.getElementById("custName")?.value.trim() || "";

        const location =
            document.getElementById("custLoc")?.value.trim() || "";

        const category =
            document.getElementById("reqCategory")?.value || "";

        const description =
            document.getElementById("reqDesc")?.value.trim() || "";


        if (!customer || !location || !category || !description) {
            alert("Please fill all the fields.");
            return;
        }


        try {

            const response = await fetch("/create-request", {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    customer: customer,
                    location: location,
                    category: category,
                    description: description
                })
            });


            if (!response.ok) {
                throw new Error(
                    `Server error: ${response.status}`
                );
            }


            const result = await response.json();


            let resultBox =
                document.getElementById("python-result");


            if (!resultBox) {

                resultBox =
                    document.createElement("div");

                resultBox.id =
                    "python-result";

                button.parentElement.appendChild(
                    resultBox
                );
            }


            if (result.success) {

                resultBox.innerHTML = `
                    <strong>✓ Technician Assigned</strong>
                    <br>
                    Technician:
                    ${result.technician}
                    <br>
                    Status:
                    ${result.status}
                `;

            } else {

                resultBox.innerHTML = `
                    <strong>⚠ No Technician Available</strong>
                    <br>
                    Status:
                    ${result.status}
                `;

            }

        } catch (error) {

            console.error(
                "FieldLink connection error:",
                error
            );

            alert(
                "Unable to connect to the Python server. Make sure app.py is running."
            );

        }

    });

});