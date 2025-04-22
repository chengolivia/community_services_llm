# PeerCopilot: A Language Model-Powered Assistant for Behavioral Health Organizations
<p align="center">
    <img src="./img/small_pull.png" width="512">
</p>

This repository contains the implementation for the paper **"PeerCopilot: A Language Model-Powered Assistant for Behavioral Health Organizations"**.

This work was done by Gao Mo*, Naveen Raman*, Megan Chai, Cindy Peng, Shannon Pagdon, Nev Jones, Hong Shen, Peggy Swarbrick, Fei Fang.

**TL;DR**

Peer-run behavioral health organizations offer holistic wellness support by combining mental health services with assistance for needs such as housing, employment, and income. However, staffing and expertise limitations hinder behavioral health organizations, making meeting all service user needs difficult. We address this issue through PeerCoPilot, a large language model (LLM)-powered assistant that helps peer providers create wellness plans, construct step-by-step goals, and find resources for these goals. Because information reliability is critical for peer providers, we designed PeerCoPilot to rely on information verified by peer providers via retrieval augmented generation. We conducted human evaluations with 15 peer providers and 6 service users and found that both groups overwhelmingly supported using PeerCoPilot. We show that PeerCoPilot provides more reliable and specific information than a baseline LLM. PeerCoPilot is now used by a group of peer providers at cspnj, a large behavioral health organization serving over 10,000 service users, and we are actively expanding PeerCoPilot's use.  


## Setup

### Installation

To set up the backend environment, first clone this repository:

```bash
git clone https://github.com/naveenr414/community_services_llm.git
```

Then install dependencies and set your OpenAI key

```bash
pip install -r requirements.txt
npm run build
export SECRET_KEY=...
```

### Running the Application

After installing dependencies run the app through the following:

```bash
npm run build
npm run start
```
PeerCoPilot will then be available at:

http://127.0.0.1:8000/