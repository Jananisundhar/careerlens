// ============================================================
// CAREERNOVA AI - MAIN JAVASCRIPT
// ============================================================

const API = {
    saveProfile: "/api/profile/save",
    analyzeCareer: "/api/analyze-career",
    skillGap: "/api/skill-gap",
    roadmap: "/api/roadmap",
    history: "/api/history",
    interviewQuestion: "/api/interview/question",
    interviewEvaluate: "/api/interview/evaluate"
};


// ============================================================
// BASIC HELPERS
// ============================================================

function $(selector) {
    return document.querySelector(selector);
}

function $$(selector) {
    return document.querySelectorAll(selector);
}


function showToast(message) {

    let toast = $("#toast");

    if (!toast) {

        toast = document.createElement("div");

        toast.id = "toast";
        toast.className = "toast";

        document.body.appendChild(toast);
    }

    toast.textContent = message;

    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
    }, 2500);
}


function escapeHtml(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


// ============================================================
// PAGE NAVIGATION
// ============================================================

function goTo(url) {
    window.location.href = url;
}


function goBack() {
    window.history.back();
}


function goHome() {
    window.location.href = "/";
}


function goLogin() {
    window.location.href = "/login";
}


function goDashboard() {
    window.location.href = "/dashboard";
}


// ============================================================
// API HELPER
// ============================================================

async function postJSON(url, data = {}) {

    const response = await fetch(url, {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify(data)
    });

    const result = await response.json();

    if (!response.ok) {
        throw new Error(
            result.message || "Something went wrong"
        );
    }

    return result;
}


async function getJSON(url) {

    const response = await fetch(url);

    const result = await response.json();

    if (!response.ok) {
        throw new Error(
            result.message || "Something went wrong"
        );
    }

    return result;
}


// ============================================================
// PROFILE DATA
// ============================================================

function getInputValue(id) {

    const element = document.getElementById(id);

    if (!element) {
        return "";
    }

    return element.value.trim();
}


function collectProfileData() {

    return {

        // Personal
        full_name: getInputValue("full_name"),
        date_of_birth: getInputValue("date_of_birth"),
        location: getInputValue("location"),

        // Education
        college: getInputValue("college"),
        degree: getInputValue("degree"),
        department: getInputValue("department"),
        current_year: getInputValue("current_year"),
        cgpa: getInputValue("cgpa"),

        // Skills
        technical_skills:
            getInputValue("technical_skills"),

        professional_skills:
            getInputValue("professional_skills"),

        creative_skills:
            getInputValue("creative_skills"),

        // Interests
        interests:
            getInputValue("interests"),

        career_interest:
            getInputValue("career_interest"),

        work_preferences:
            getInputValue("work_preferences"),

        // Projects
        projects:
            getInputValue("projects"),

        experience:
            getInputValue("experience"),

        certifications:
            getInputValue("certifications"),

        achievements:
            getInputValue("achievements")
    };
}


// ============================================================
// SAVE PROFILE
// ============================================================

async function saveCurrentProfile(nextPage = null) {

    const data = collectProfileData();

    try {

        await postJSON(API.saveProfile, data);

        showToast("Profile saved successfully ✓");

        if (nextPage) {

            setTimeout(() => {
                window.location.href = nextPage;
            }, 350);
        }

    } catch (error) {

        console.error(error);

        showToast(
            error.message ||
            "Unable to save profile"
        );
    }
}


// ============================================================
// LOAD PROFILE INTO FORM
// ============================================================

async function loadProfileIntoForm() {

    /*
       Profile loading will be connected to the
       database-backed profile endpoint later.

       For now this safely checks if fields exist.
    */

    return true;
}


// ============================================================
// CAREER ANALYSIS
// ============================================================

async function startCareerAnalysis() {

    const status = $("#analysis-status");

    if (status) {
        status.textContent =
            "CareerNova AI is understanding your profile...";
    }

    try {

        const result =
            await postJSON(
                API.analyzeCareer,
                {}
            );

        if (status) {

            status.textContent =
                result.message ||
                "Analysis completed.";
        }

        if (result.success) {

            setTimeout(() => {
                window.location.href = "/matches";
            }, 900);
        }

    } catch (error) {

        console.error(error);

        if (status) {

            status.textContent =
                "AI analysis could not be completed.";
        }

        showToast(
            error.message ||
            "AI analysis failed"
        );
    }
}


// ============================================================
// CAREER MATCH SELECTION
// ============================================================

function selectCareer(
    careerName,
    careerCategory = ""
) {

    localStorage.setItem(
        "careerNovaTargetCareer",
        careerName
    );

    localStorage.setItem(
        "careerNovaTargetCategory",
        careerCategory
    );

    showToast(
        `${careerName} selected`
    );

    setTimeout(() => {

        window.location.href =
            "/skill-gap";

    }, 500);
}


function getSelectedCareer() {

    return localStorage.getItem(
        "careerNovaTargetCareer"
    ) || "";
}


// ============================================================
// SKILL GAP
// ============================================================

async function loadSkillGap() {

    const container =
        $("#skill-gap-container");

    const career =
        getSelectedCareer();

    const title =
        $("#selected-career-name");

    if (title) {

        title.textContent =
            career ||
            "Your selected career";
    }

    try {

        const result =
            await postJSON(
                API.skillGap,
                {
                    career: career
                }
            );

        if (
            container &&
            result.message
        ) {

            container.innerHTML = `
                <div class="card">
                    <div class="card-title">
                        AI Skill Gap Analysis
                    </div>

                    <p class="card-description">
                        ${escapeHtml(result.message)}
                    </p>
                </div>
            `;
        }

    } catch (error) {

        console.error(error);

        if (container) {

            container.innerHTML = `
                <div class="error-message">
                    Unable to load skill gap analysis.
                </div>
            `;
        }
    }
}


// ============================================================
// ROADMAP
// ============================================================

async function loadRoadmap() {

    const container =
        $("#roadmap-container");

    const career =
        getSelectedCareer();

    const title =
        $("#roadmap-career");

    if (title) {

        title.textContent =
            career ||
            "Your selected career";
    }

    try {

        const result =
            await postJSON(
                API.roadmap,
                {
                    career: career
                }
            );

        if (
            container &&
            result.message
        ) {

            container.innerHTML = `
                <div class="card">
                    <div class="card-title">
                        Personalized AI Roadmap
                    </div>

                    <p class="card-description">
                        ${escapeHtml(result.message)}
                    </p>
                </div>
            `;
        }

    } catch (error) {

        console.error(error);
    }
}


// ============================================================
// 10-QUESTION CAREER ASSESSMENT
// ============================================================

const careerAssessment = {

    currentQuestion: 0,

    answers: [],

    questions: []
};


// ------------------------------------------------------------
// Default question structure
// ------------------------------------------------------------

function getDefaultAssessmentQuestions() {

    return [

        {
            question:
                "When you face a difficult problem, what do you naturally enjoy doing?",

            options: [
                "Finding a logical or technical solution",
                "Understanding people and their needs",
                "Researching information and comparing possibilities",
                "Creating a new or unusual approach"
            ]
        },

        {
            question:
                "Which type of work feels most interesting to you?",

            options: [
                "Working with technology, data or systems",
                "Working with people, communication or guidance",
                "Working with business, money or planning",
                "Creating content, designs or new ideas"
            ]
        },

        {
            question:
                "When learning something new, what is your strongest approach?",

            options: [
                "Practice it until I can do it myself",
                "Discuss it with someone and understand the concept",
                "Read, research and compare different sources",
                "Experiment and learn through creativity"
            ]
        },

        {
            question:
                "Which situation would make you feel most satisfied?",

            options: [
                "Solving a challenging problem",
                "Helping someone achieve their goal",
                "Making an important decision or plan",
                "Creating something people appreciate"
            ]
        },

        {
            question:
                "What kind of responsibility would you prefer?",

            options: [
                "Managing systems, technology or information",
                "Supporting, teaching or communicating with people",
                "Managing money, operations or decisions",
                "Managing creative work or new ideas"
            ]
        },

        {
            question:
                "Which skill would you most like to become excellent at?",

            options: [
                "Analysis and problem solving",
                "Communication and people skills",
                "Leadership and decision making",
                "Creativity and innovation"
            ]
        },

        {
            question:
                "How do you usually approach an important decision?",

            options: [
                "I analyse facts and evidence",
                "I consider how it affects people",
                "I compare risks, benefits and outcomes",
                "I think of different possibilities first"
            ]
        },

        {
            question:
                "Which working environment sounds most comfortable?",

            options: [
                "A structured environment with clear problems to solve",
                "A people-focused environment",
                "A professional environment involving planning and decisions",
                "A flexible environment where I can create and experiment"
            ]
        },

        {
            question:
                "What kind of achievement would make you most proud?",

            options: [
                "Building or solving something difficult",
                "Helping or teaching someone successfully",
                "Leading a successful project or decision",
                "Creating something original"
            ]
        },

        {
            question:
                "If you had one year to become excellent at one area, which would you choose?",

            options: [
                "Technology, analysis or research",
                "Communication, teaching or people development",
                "Business, finance or leadership",
                "Design, media or creative innovation"
            ]
        }

    ];
}


// ============================================================
// START ASSESSMENT
// ============================================================

function startCareerAssessment(
    questions = null
) {

    careerAssessment.currentQuestion = 0;

    careerAssessment.answers = [];

    careerAssessment.questions =
        questions ||
        getDefaultAssessmentQuestions();

    renderAssessmentQuestion();
}


// ============================================================
// RENDER QUESTION
// ============================================================

function renderAssessmentQuestion() {

    const questionContainer =
        $("#assessment-question");

    const optionsContainer =
        $("#assessment-options");

    if (
        !questionContainer ||
        !optionsContainer
    ) {
        return;
    }

    const questions =
        careerAssessment.questions;

    const index =
        careerAssessment.currentQuestion;

    const current =
        questions[index];

    if (!current) {

        finishCareerAssessment();

        return;
    }

    questionContainer.innerHTML = `
        <div class="question-number">
            QUESTION ${index + 1} / ${questions.length}
        </div>

        <div class="question-text">
            ${escapeHtml(current.question)}
        </div>
    `;

    optionsContainer.innerHTML = "";

    current.options.forEach(
        (option, optionIndex) => {

            const letter =
                String.fromCharCode(
                    65 + optionIndex
                );

            const button =
                document.createElement("div");

            button.className = "option";

            button.innerHTML = `
                <span class="option-letter">
                    ${letter}
                </span>

                <span>
                    ${escapeHtml(option)}
                </span>
            `;

            button.addEventListener(
                "click",
                () => {

                    selectAssessmentAnswer(
                        optionIndex,
                        option
                    );

                }
            );

            optionsContainer.appendChild(
                button
            );
        }
    );

    updateAssessmentProgress();
}


// ============================================================
// SELECT ANSWER
// ============================================================

function selectAssessmentAnswer(
    optionIndex,
    optionText
) {

    const index =
        careerAssessment.currentQuestion;

    careerAssessment.answers[index] = {

        question:
            careerAssessment.questions[index]
                .question,

        selected_option:
            optionText,

        selected_index:
            optionIndex,

        selected_letter:
            String.fromCharCode(
                65 + optionIndex
            )
    };

    $$(".option").forEach(
        (element, i) => {

            element.classList.toggle(
                "selected",
                i === optionIndex
            );
        }
    );

    const nextButton =
        $("#assessment-next");

    if (nextButton) {

        nextButton.disabled = false;
        nextButton.style.opacity = "1";
    }
}


// ============================================================
// NEXT QUESTION
// ============================================================

function nextAssessmentQuestion() {

    const index =
        careerAssessment.currentQuestion;

    if (
        !careerAssessment.answers[index]
    ) {

        showToast(
            "Please select one option"
        );

        return;
    }

    careerAssessment.currentQuestion++;

    if (
        careerAssessment.currentQuestion >=
        careerAssessment.questions.length
    ) {

        finishCareerAssessment();

        return;
    }

    renderAssessmentQuestion();
}


// ============================================================
// PREVIOUS QUESTION
// ============================================================

function previousAssessmentQuestion() {

    if (
        careerAssessment.currentQuestion <= 0
    ) {
        return;
    }

    careerAssessment.currentQuestion--;

    renderAssessmentQuestion();
}


// ============================================================
// PROGRESS
// ============================================================

function updateAssessmentProgress() {

    const total =
        careerAssessment.questions.length;

    const current =
        careerAssessment.currentQuestion + 1;

    const percentage =
        (current / total) * 100;

    const fill =
        $("#assessment-progress");

    if (fill) {

        fill.style.width =
            `${percentage}%`;
    }

    const count =
        $("#assessment-count");

    if (count) {

        count.textContent =
            `${current} / ${total}`;
    }
}


// ============================================================
// FINISH ASSESSMENT
// ============================================================

function finishCareerAssessment() {

    const answers =
        careerAssessment.answers;

    localStorage.setItem(
        "careerNovaAssessmentAnswers",
        JSON.stringify(answers)
    );

    showToast(
        "Assessment completed ✓"
    );

    setTimeout(() => {

        window.location.href =
            "/analysis";

    }, 600);
}


// ============================================================
// GET ASSESSMENT ANSWERS
// ============================================================

function getAssessmentAnswers() {

    try {

        return JSON.parse(
            localStorage.getItem(
                "careerNovaAssessmentAnswers"
            )
        ) || [];

    } catch {

        return [];
    }
}


// ============================================================
// HISTORY
// ============================================================

async function loadHistory() {

    const container =
        $("#history-container");

    if (!container) {
        return;
    }

    try {

        const result =
            await getJSON(API.history);

        if (
            !result.history ||
            result.history.length === 0
        ) {

            container.innerHTML = `
                <div class="empty-state">
                    No activity yet.
                </div>
            `;

            return;
        }

        container.innerHTML =
            result.history
                .map(item => {

                    return `
                        <div class="history-item">

                            <div>

                                <div class="history-type">
                                    ${escapeHtml(
                        item.activity_type
                    )}
                                </div>

                                <div class="history-title">
                                    ${escapeHtml(
                        item.title
                    )}
                                </div>

                            </div>

                            <div class="history-date">
                                ${escapeHtml(
                        item.created_at
                    )}
                            </div>

                        </div>
                    `;

                })
                .join("");

    } catch (error) {

        console.error(error);

        container.innerHTML = `
            <div class="error-message">
                Unable to load history.
            </div>
        `;
    }
}


// ============================================================
// MOCK INTERVIEW
// ============================================================

let currentInterviewQuestion = "";


async function getInterviewQuestion() {

    const questionBox =
        $("#interview-question");

    if (!questionBox) {
        return;
    }

    const career =
        getSelectedCareer();

    try {

        const result =
            await postJSON(
                API.interviewQuestion,
                {
                    career: career
                }
            );

        currentInterviewQuestion =
            result.question || "";

        questionBox.textContent =
            currentInterviewQuestion;

    } catch (error) {

        console.error(error);

        questionBox.textContent =
            "Tell me about yourself and why you are interested in this career.";
    }
}


async function evaluateInterviewAnswer(
    answer
) {

    const career =
        getSelectedCareer();

    try {

        const result =
            await postJSON(
                API.interviewEvaluate,
                {
                    career: career,

                    question:
                        currentInterviewQuestion,

                    answer: answer
                }
            );

        return result;

    } catch (error) {

        console.error(error);

        return {
            success: false
        };
    }
}


// ============================================================
// CAMERA
// ============================================================

let cameraStream = null;


async function startCamera() {

    const video =
        $("#camera-video");

    if (!video) {
        return;
    }

    try {

        cameraStream =
            await navigator.mediaDevices.getUserMedia({
                video: true,
                audio: true
            });

        video.srcObject =
            cameraStream;

    } catch (error) {

        console.error(error);

        showToast(
            "Camera permission is required for mock interview."
        );
    }
}


function stopCamera() {

    if (!cameraStream) {
        return;
    }

    cameraStream
        .getTracks()
        .forEach(track => {
            track.stop();
        });

    cameraStream = null;
}


// ============================================================
// SPEECH RECOGNITION
// ============================================================

let speechRecognition = null;
let speechText = "";


function startSpeechRecognition() {

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    if (!SpeechRecognition) {

        showToast(
            "Speech recognition is not supported in this browser."
        );

        return;
    }

    speechRecognition =
        new SpeechRecognition();

    speechRecognition.continuous = true;

    speechRecognition.interimResults = true;

    speechRecognition.lang = "en-IN";

    speechRecognition.onresult =
        function (event) {

            let finalText = "";

            for (
                let i = event.resultIndex;
                i < event.results.length;
                i++
            ) {

                const transcript =
                    event.results[i][0]
                        .transcript;

                if (
                    event.results[i].isFinal
                ) {

                    finalText +=
                        transcript + " ";
                }
            }

            speechText += finalText;

            const box =
                $("#answer-text");

            if (box) {

                box.value =
                    speechText;
            }
        };

    speechRecognition.start();
}


function stopSpeechRecognition() {

    if (speechRecognition) {

        speechRecognition.stop();

        speechRecognition = null;
    }
}


// ============================================================
// AUTO INITIALIZATION
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        // History page
        if ($("#history-container")) {
            loadHistory();
        }

        // Assessment page
        if (
            $("#assessment-question") &&
            $("#assessment-options")
        ) {

            startCareerAssessment();
        }

        // Skill gap page
        if ($("#skill-gap-container")) {
            loadSkillGap();
        }

        // Roadmap page
        if ($("#roadmap-container")) {
            loadRoadmap();
        }

        // Interview page
        if ($("#camera-video")) {

            startCamera();
            getInterviewQuestion();
        }

    }
);