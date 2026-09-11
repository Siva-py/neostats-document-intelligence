const API_BASE_URL = window.location.hostname === "localhost"
    ? "http://127.0.0.1:8000"
    : "https://neostats-document-intelligence-api.onrender.com";

const fileInput = document.getElementById("file-input");
const documentType = document.getElementById("document-type");
const processButton = document.getElementById("process-button");
const hideResultButton =
    document.getElementById("hide-result-button");

const resultSection =
    document.getElementById("result-section");

const message = document.getElementById("message");

const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");


    const dashboardNav = document.querySelector(
    '.nav-item:nth-child(1)'
);

const processNav = document.querySelector(
    '.nav-item:nth-child(2)'
);

const documentsNav = document.querySelector(
    '.nav-item:nth-child(4)'
);

const heroSection = document.querySelector(
    '.hero-banner'
);

const processSection = document.querySelector(
    '.process-card'
);

const mainContent =
    document.querySelector(".main-content");

const documentsSection = document.querySelector(
    '.documents-card'

);
const copyJsonButton =
    document.getElementById("copy-json-button");

hideResultButton.addEventListener("click", () => {
    resultSection.style.display = "none";
});

dashboardNav.addEventListener("click", (event) => {

    event.preventDefault();

    setActiveNav(dashboardNav);

    mainContent.scrollTo({
        top: 0,
        behavior: "smooth"
    });

});


processNav.addEventListener("click", (event) => {

    event.preventDefault();

    setActiveNav(processNav);

    resultSection.style.display = "none";

    const targetTop =
        processSection.getBoundingClientRect().top
        - mainContent.getBoundingClientRect().top
        + mainContent.scrollTop
        - 20;

    mainContent.scrollTo({
        top: targetTop,
        behavior: "smooth"
    });

});

documentsNav.addEventListener("click", (event) => {

    event.preventDefault();
    setActiveNav(documentsNav);

    documentsSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

    loadDocuments();

});

copyJsonButton.addEventListener("click", async () => {

    const rawJson =
        document.getElementById("raw-json");

    try {

        await navigator.clipboard.writeText(
            rawJson.textContent
        );

        copyJsonButton.textContent = "✓ Copied";

        setTimeout(() => {
            copyJsonButton.textContent = "Copy JSON";
        }, 1500);

    } catch (error) {

        copyJsonButton.textContent = "Copy failed";

    }

});

async function checkApiHealth() {

    try {
        const response = await fetch(
            `${API_BASE_URL}/api/v1/health`
        );

        if (!response.ok) {
            throw new Error("API unavailable");
        }

        statusDot.classList.remove("offline");
        statusDot.classList.add("online");

        statusText.textContent = "API Connected";

    } catch (error) {

        statusDot.classList.remove("online");
        statusDot.classList.add("offline");

        statusText.textContent = "API Offline";

    }
}


async function processDocument() {

    const file = fileInput.files[0];

    if (!file) {
        message.textContent = "Please select a document.";
        return;
    }

    processButton.disabled = true;
    processButton.textContent = "Processing...";
    message.textContent =
        "Uploading and processing document...";

    const formData = new FormData();

    formData.append("file", file);
    formData.append(
        "document_type",
        documentType.value
    );

    try {

        const response = await fetch(
            `${API_BASE_URL}/api/v1/documents/process`,
            {
                method: "POST",
                body: formData
            }
        );

        const result = await response.json();

        if (!response.ok) {

            const errorMessage =
                typeof result.detail === "object"
                    ? result.detail.message
                    : result.detail;

            throw new Error(
                errorMessage || "Document processing failed."
            );
        }

        console.log("Processing result:", result);

        displayResult(result);

            message.textContent =
                "✓ Document processed successfully.";

            window.scrollTo({
            top: -1,
            behavior: "smooth"
        });

    } catch (error) {

        console.error(error);

        if (
                error.message.includes(
                    "All configured Gemini API keys"
                )
            ) {
                message.textContent =
                    `⚠ AI Processing Unavailable: ${error.message}`;
                message.style.color = "#b45309";
            } else {
                message.textContent =
                    `Error: ${error.message}`;
                message.style.color = "#b91c1c";
            }

    } finally {

        processButton.disabled = false;
        processButton.textContent =
            "⚙  Process Document";
    }
}

function displayResult(result) {

    const resultSection =
        document.getElementById("result-section");

    const resultSummary =
        document.getElementById("result-summary");

    const resultStatus =
        document.getElementById("result-status");

    const resultContent =
        document.getElementById("result-content");


    resultSection.style.display = "block";


    const status =
        result.status || "UNKNOWN";


    resultStatus.textContent = status;

    resultStatus.classList.toggle(
        "failed",
        status === "FAILED"
    );


    resultSummary.textContent =
        `${result.document_name || "Document"} · ${result.document_type || ""}`;


    const extraction =
        result.extraction || {};

    const statement =
        extraction.financial_statement || {};

    const sections =
        statement.sections || [];

    const validation =
        result.financial_validation || {};


    let html = "";


    /* =========================
       METADATA
       ========================= */

    html += `
        <div class="result-grid">

            <div class="result-info">
                <div class="result-info-label">
                    Document
                </div>

                <div class="result-info-value">
                    ${escapeHtml(result.document_name || "N/A")}
                </div>
            </div>


            <div class="result-info">
                <div class="result-info-label">
                    Document Type
                </div>

                <div class="result-info-value">
                    ${escapeHtml(result.document_type || "N/A")}
                </div>
            </div>


            <div class="result-info">
                <div class="result-info-label">
                    As At / Date
                </div>

                <div class="result-info-value">
                    ${escapeHtml(extraction.as_at_date || "N/A")}
                </div>
            </div>


            <div class="result-info">
                <div class="result-info-label">
                    Unit of Measurement
                </div>

                <div class="result-info-value">
                    ${escapeHtml(
                        extraction.unit_of_measurement || "N/A"
                    )}
                </div>
            </div>


            <div class="result-info">
                <div class="result-info-label">
                    Comparative Periods
                </div>

                <div class="result-info-value">
                    ${
                        extraction.comparative_periods?.length
                            ? escapeHtml(
                                extraction.comparative_periods.join(", ")
                              )
                            : "N/A"
                    }
                </div>
            </div>


            <div class="result-info">
                <div class="result-info-label">
                    Processing Status
                </div>

                <div class="result-info-value">
                    ${escapeHtml(status)}
                </div>
            </div>

        </div>
    `;


    /* =========================
       EXTRACTED SECTIONS
       ========================= */

    if (sections.length > 0) {

        html += `
            <div class="result-block">

                <h3>Extracted Information</h3>

                <p class="result-block-description">
                    Structured information extracted from the document.
                </p>
        `;


        sections.forEach(section => {

            html += `
                <div class="extraction-section">

                    <h4>
                        ${escapeHtml(
                            section.section_name || "Section"
                        )}
                    </h4>
            `;


            const items =
                section.line_items || [];


            if (items.length === 0) {

                html += `
                    <p class="no-data">
                        No extracted fields.
                    </p>
                `;

            } else {

                html += `
                    <div class="extraction-table-wrapper">

                        <table class="extraction-table">

                            <thead>
                                <tr>
                                    <th>Field</th>
                                    <th>Values</th>
                                    <th>Evidence</th>
                                </tr>
                            </thead>

                            <tbody>
                `;


                items.forEach(item => {

                    const values =
                        item.values || {};

                    const valueEntries =
                        Object.entries(values);


                    let valueHtml = "";


                    if (valueEntries.length === 0) {

                        valueHtml = "N/A";

                    } else {

                        valueHtml =
                            valueEntries
                                .map(
                                    ([key, value]) => `
                                        <div class="value-row">
                                            <span class="value-key">
                                                ${escapeHtml(key)}
                                            </span>

                                            <span class="value-data">
                                                ${escapeHtml(
                                                    value ?? "null"
                                                )}
                                            </span>
                                        </div>
                                    `
                                )
                                .join("");
                    }


                    const evidence =
                        item.evidence || {};

                    const evidenceText =
                        evidence.source_text || "";

                    const pageNumber =
                        evidence.page_number;


                    html += `
                        <tr>

                            <td class="field-name">
                                ${escapeHtml(
                                    item.line_item || "N/A"
                                )}

                                ${
                                    item.schedule
                                        ? `
                                            <div class="field-schedule">
                                                ${escapeHtml(
                                                    item.schedule
                                                )}
                                            </div>
                                          `
                                        : ""
                                }
                            </td>


                            <td>
                                ${valueHtml}
                            </td>


                            <td class="evidence-cell">

                                ${
                                    pageNumber
                                        ? `<span class="page-badge">
                                            Page ${pageNumber}
                                           </span>`
                                        : ""
                                }

                                ${
                                    evidenceText
                                        ? `
                                            <div class="evidence-text">
                                                ${escapeHtml(
                                                    evidenceText
                                                )}
                                            </div>
                                          `
                                        : "No evidence available"
                                }

                            </td>

                        </tr>
                    `;
                });


                html += `
                            </tbody>

                        </table>

                    </div>
                `;
            }


            html += `
                </div>
            `;
        });


        html += `
            </div>
        `;
    }


    /* =========================
       FINANCIAL VALIDATION
       ========================= */

    const validationStatus =
        validation.status;


    html += `
        <div class="result-block">

            <div class="validation-header">

                <div>
                    <h3>Financial Validation</h3>

                    <p class="result-block-description">
                        Automated financial consistency checks.
                    </p>
                </div>

                <span class="
                    validation-badge
                    ${
                        validationStatus === "PASS"
                            ? "validation-pass"
                            : validationStatus === "FAILED"
                                ? "validation-fail"
                                : ""
                    }
                ">
                    ${escapeHtml(
                        validationStatus || "NOT_APPLICABLE"
                    )}
                </span>

            </div>
    `;


    const checks =
        validation.checks ||
        validation.results ||
        [];


    if (checks.length > 0) {

        html += `
            <div class="validation-list">
        `;


        checks.forEach(check => {

            const checkStatus =
                check.status || "NOT_APPLICABLE";


            html += `
                <div class="validation-item">

                    <div class="validation-item-main">

                        <div class="validation-check-name">
                            ${escapeHtml(
                                check.check || "Validation Check"
                            )}
                        </div>

                        <div class="validation-formula">
                            ${escapeHtml(
                                check.formula || ""
                            )}
                        </div>

                    </div>


                    <span class="
                        validation-check-status
                        ${
                            checkStatus === "PASS"
                                ? "check-pass"
                                : checkStatus === "FAIL"
                                    ? "check-fail"
                                    : "check-na"
                        }
                    ">
                        ${escapeHtml(checkStatus)}
                    </span>

                </div>
            `;
        });


        html += `
            </div>
        `;

    } else {

        html += `
            <div class="no-data">
                No validation checks available.
            </div>
        `;
    }


    html += `
        </div>
    `;


    resultContent.innerHTML = html;

const rawJson = document.getElementById("raw-json");

rawJson.textContent = JSON.stringify(
    result,
    null,
    2
);
}

function escapeHtml(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

processButton.addEventListener(
    "click",
    processDocument
);


checkApiHealth();
setInterval(checkApiHealth, 10000);

fileInput.addEventListener("change", () => {

    const file = fileInput.files[0];

    if (!file) {
        return;
    }

    const uploadZone = document.querySelector(".upload-zone");

    uploadZone.querySelector("h3").textContent =
        file.name;

    uploadZone.querySelector("p").textContent =
        "Ready to process";

    uploadZone.querySelector(".upload-or").textContent =
        `${(file.size / 1024).toFixed(1)} KB`;

});

async function loadDocuments() {

    const documentsList =
        document.getElementById("documents-list");

    documentsList.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">↻</div>
            <h3>Loading documents...</h3>
            <p>Retrieving processed documents.</p>
        </div>
    `;

    try {

        const response = await fetch(
            `${API_BASE_URL}/api/v1/documents`
        );

        if (!response.ok) {
            throw new Error(
                "Failed to load documents."
            );
        }

        const documents =
            await response.json();

        if (!documents.length) {

            documentsList.innerHTML = `
                <div class="empty-state">

                    <div class="empty-icon">
                        ▤
                    </div>

                    <h3>
                        No documents yet
                    </h3>

                    <p>
                        Process a document to see it appear here.
                    </p>

                </div>
            `;

            return;
        }


        documentsList.innerHTML = documents
            .map(document => {

                const statusClass =
                    document.status === "PASS"
                        ? "document-status-pass"
                        : "document-status-fail";

                return `
                    <div class="document-row">

                        <div class="document-row-main">

                            <div class="document-row-icon">
                                ▤
                            </div>

                            <div>

                                <div class="document-name">
                                    ${escapeHtml(
                                        document.document_name
                                    )}
                                </div>

                                <div class="document-meta">
                                    ${escapeHtml(
                                        document.document_type
                                    )}
                                    ·
                                    ${escapeHtml(
                                        document.created_at
                                    )}
                                </div>

                            </div>

                        </div>


                        <div class="document-row-right">

                            <span class="
                                document-status
                                ${statusClass}
                            ">
                                ${escapeHtml(
                                    document.status
                                )}
                            </span>

                            <button
                                class="view-document-button"
                                data-document-name="${escapeHtml(
                                    document.document_name
                                )}"
                            >
                                View
                            </button>

                        </div>

                    </div>
                `;

            })
            .join("");


        document
            .querySelectorAll(".view-document-button")
            .forEach(button => {

                button.addEventListener(
                    "click",
                    () => {

                        const documentName =
                            button.dataset.documentName;

                        loadDocumentResult(
                            documentName
                        );
                    }
                );

            });

    } catch (error) {

        documentsList.innerHTML = `
            <div class="empty-state">

                <div class="empty-icon">
                    !
                </div>

                <h3>
                    Unable to load documents
                </h3>

                <p>
                    ${escapeHtml(error.message)}
                </p>

            </div>
        `;
    }
}
async function loadDocumentResult(documentName) {

    try {

        const response = await fetch(
            `${API_BASE_URL}/api/v1/documents/${encodeURIComponent(
                documentName
            )}`
        );

        if (!response.ok) {
            throw new Error(
                "Failed to retrieve document."
            );
        }

        const storedDocument =
            await response.json();

        displayResult(
            storedDocument.result
        );

        const resultSection =
            document.getElementById("result-section");

        resultSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    } catch (error) {

        message.textContent =
            `Error: ${error.message}`;
    }
}

const refreshButton =
    document.getElementById("refresh-button");

refreshButton.addEventListener(
    "click",
    loadDocuments
);
loadDocuments();

function setActiveNav(activeItem) {

    document
        .querySelectorAll(".nav-item")
        .forEach(item => {
            item.classList.remove("active");
        });

    activeItem.classList.add("active");
}
const intelligenceText = document.querySelector(
    ".topbar h1 span"
);

if (intelligenceText) {

    const fullText = intelligenceText.textContent.trim();

    intelligenceText.textContent = "";

    let index = 0;

    function typeIntelligence() {

        if (index < fullText.length) {

            intelligenceText.textContent +=
                fullText[index];

            index++;

            setTimeout(
                typeIntelligence,
                90
            );

        }

    }

    setTimeout(
        typeIntelligence,
        400
    );
}