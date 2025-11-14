![CoverIQ](Demo_Images/Logo.png)
<p align="center">
    <a href="https://www.appier.com/en/">
        <img alt="Appier" src="https://img.shields.io/badge/Organization-Appier-blue">
    </a>
    <a href="https://www.appier.com/en/">
        <img alt="Appier" src="https://img.shields.io/badge/Team-Personalization_Cloud_QA-navy">
    </a>
    <a href="https://www.appier.com/en/">
        <img alt="Appier" src="https://img.shields.io/badge/Appier_2025_Hackathon-Practical_Impact_Award--2nd_Place-default">
    </a>
</p>

# QAgent
### [Setup Guide](./qagent/README.md)
> ### Don’t just automate tests. Automate your tasks! 

QAgent is an AI-powered pipeline that automates the creation of QA documentation. By leveraging the Gemini API to digest product requirements (PRDs) and Figma designs, it generates comprehensive test plans and cases, freeing up engineers to focus on high-impact validation and optimization.

![Landing Page](Demo_Images/QAgent_Landing_Page.png)

Full Description and Showcased Demo here (Appier folks only): https://appier.atlassian.net/wiki/spaces/Labs/pages/4144693249/TEAM+CoverIQ+QA+Workflow+Automation+with+QAgent+An+AI-Powered+Test+Planner

-----

### Table of Contents

1.  [The Challenge](https://www.google.com/search?q=%23the-challenge)
2.  [The Solution](https://www.google.com/search?q=%23the-solution)
3.  [Impact Metrics](https://www.google.com/search?q=%23impact-metrics)
4.  [Our Journey: From Mega-Prompt to a 3-Stage Pipeline](https://www.google.com/search?q=%23our-journey-from-mega-prompt-to-a-3-stage-pipeline)
5.  [Key Takeaways](https://www.google.com/search?q=%23key-takeaways)
6.  [Project Information](https://www.google.com/search?q=%23project-information)

-----

## The Challenge

Our QA process was bottlenecked by the manual, time-consuming task of translating product requirements and Figma designs into actionable test plans. This foundational work delayed actual testing and kept our team buried in documentation.

## The Solution

QAgent uses the Gemini API to automatically summarize PRDs, analyze designs, and generate comprehensive test documentation. This allows our team to shift focus from manual creation to strategic review and validation, using AI as a collaborative partner to refine test strategies.

## Impact Metrics

#### **Qualitative**

QAgent generates extensive test cases with high coverage, serving as an excellent "Step 0" for new feature testing. It frees up engineers to focus on higher-impact quality tasks like exploratory testing and demonstrates powerful new possibilities for automating the Software Testing Life Cycle (STLC).

#### **Quantitative**

**Time Comparison:**

| Task | Manual Workflow | With QAgent (AI-Assisted) |
| :--- | :--- | :--- |
| Document Digestion (PRD & Figma) | Hours | **\~30 seconds** (summarized) |
| Test Plan Documentation | Often skipped | **2-3 minutes** (generated) |
| Test Case Documentation | Up to a full day | **\~3 minutes** (for 80 cases) |

**Generated Case Quality:**
In a sample run of 27 generated test cases, **48%** were directly usable, and another **29%** were usable with modification.

## Our Journey: From Mega-Prompt to a 3-Stage Pipeline

Our path to a working solution involved significant iteration.

  * **Initial Approach: The “Mega-Prompt”**
    Our first attempt used a single, massive prompt to process raw PRD and Figma data. It failed due to token limits, input noise, and inconsistent results.

  * **Pivot \#1: Filtering & Two-Step Processing**
    We then implemented a Python filter for Figma JSON and a two-step flow. This improved focus but still struggled with complex designs and inconsistent output.

  * **Pivot \#2: The Three-Stage Pipeline**
    Our final, successful architecture is a modular pipeline:

    1.  **Extract:** Use specialized AI personas to pull key context from inputs.
    2.  **Summarize:** Condense the extracted data into a token-efficient format.
    3.  **Generate:** Create the test plan and cases, then export them directly to TestRail.

## Key Takeaways

1.  **Modularity Over Monoliths:** A multi-stage pipeline is far more reliable and scalable than a single, complex prompt.

2.  **Pre-process Raw Inputs:** Cleaning and filtering data (like Figma JSON) before sending it to the model is critical for reducing noise and improving focus.

3.  **Mitigate Compounding Errors:** Small errors in early stages can ruin the final output. We address this by offering two modes:

      * **Trust Mode:** A fully automated, one-step execution.
      * **Supervised Mode:** Integrates manual review checkpoints between stages.

## Project Information
  * **Team Members:**
      * james.tu@appier.com 
      * liam.sun@appier.com 
  * **Workflow Areas Impacted:**
      * Feature Document/Design Digestion, Test Planning, Test Case Design, Documentation
