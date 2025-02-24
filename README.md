# Peer Copilot: A Language Model-Powered Assistant for Behavioral Health Organizations

![Figure](./img/small_pull.png)  

This repository contains the implementation for the paper **"Peer Copilot: A Language Model-Powered Assistant for Behavioral Health Organizations"**, published at __.

This work was done by __.

**TL;DR**

Peer-run behavioral health organizations offer holistic assistance for mental health illnesses and substance use disorders through peer supporters, who help service users obtain recovery and wellness resources. Unfortunately, staffing and expertise limitations significantly hinder the operations of behavioral health organizations, making it hard to match all service user needs. 

We address this issue through **Peer Copilot**, a language model-powered assistant that helps peer supporters discover resources, navigate government benefit programs, and construct goals for service users.Because information reliability is critical for peer supporters, we designed Peer Copilot to rely on verified information sources and avoid hallucinations.  

Empirically, we conducted human evaluations with 14 peer supporters and 6 service users and found that both groups overwhelmingly supported using Peer Copilot in practice. Peer Copilot is now used by a group of peer supporters in a large behavioral health organization, and we are actively expanding the use of Peer Copilot. 



## Citation

If you use our code for your research, please cite this as:

```bibtex
@article{__,
  title={Peer Copilot: A Language Model-Powered Assistant for Behavioral Health Organizations},
  author={__},
  journal={__}, 
  year={2025}
}
```

## Setup

### Backend Installation

To set up the backend environment, first clone this repository:

```bash
git clone https://github.com/naveenr414/community_services_llm.git
```

Then, navigate into the **backend** folder and install the dependencies:

```bash
cd backend
conda env create --file env.yaml
conda activate peer-copilot
```

### Frontend Installation

To set up the frontend, navigate into the **frontend-react** folder and install dependencies using npm:

```bash
cd frontend-react
npm install
```

### Running the Application

After installing dependencies for both the backend and frontend, follow these steps to run the application:

#### Start the backend:
```bash
cd backend
uvicorn all_endpoints:socket_app --reload --port 8000
```

#### Start the frontend:
Open a new terminal and run:
```bash
cd frontend-react
npm start
```

Once both services are running, the tool will be available at:

http://localhost:3000/

### PeerCoPilot User Tutorial 

[Tutorial](https://www.youtube.com/watch?v=4rg1wmo2Y8w)




