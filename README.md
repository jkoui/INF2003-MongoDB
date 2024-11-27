<!-- @format -->

## Installation and Hosting Guide
### Front-end (ReactJS)  
• Make sure node.js is downloaded and updated to install dependencies  
• From the root folder, “cd client”, “npm install” to install dependencies  
• “npm run dev” to run the website locally and visit localhost:5173 to view the GUI 

### Back-end (Flask)
• Make sure python is installed and updated  
• From the root folder, “cd server”  
• Run “pip install -r requirements.txt” or make a virtual environment before installing to install the required dependencies  
• Run “flask --app webserver run” to run the flask server locally  

### Running on Docker
• Make sure Docker Desktop app is downloaded  
• Go to root folder  
• Run "docker-compose up --build"  

### Deploying on Edge
• Set up AWS EC2 instance with cloned project
• Install Docker on instance and run "docker-compose up --build"  
• Deploy EC2 instance on Amazon Cloudfront after buying a domain
