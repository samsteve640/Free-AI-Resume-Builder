import os, tempfile
from flask import Flask, render_template, request, redirect, url_for, send_file, session
from dotenv import load_dotenv
from openai import OpenAI
from weasyprint import HTML
import stripe

load_dotenv()
app = Flask(__name__)
@app.route('/debug-routes')
def list_routes():
    import urllib
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        line = urllib.parse.unquote(f"{rule.endpoint:20s} {methods:20s} {rule}")
        output.append(line)
    return "<pre>" + "\n".join(output) + "</pre>"
app.secret_key = os.getenv('FLASK_SECRET','secret')

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
BASE_URL = os.getenv('BASE_URL','http://localhost:5000')

roles = [
    "software-engineer",
    "data-analyst",
    "nurse",
    "teacher",
    "project-manager",
    "marketing-manager",
    "accountant",
    "graphic-designer",
    "web-developer",
    "hr-manager"
]

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/builder', methods=['GET','POST'])
def builder():
    if request.method == 'POST':
        name = request.form['name']
        title = request.form['title']
        skills = request.form['skills']
        experience = request.form['experience']
        prompt = f'''Create a clean ATS-friendly resume in HTML sections for:\nName:{name}\nRole:{title}\nSkills:{skills}\nExperience:{experience}\nUse concise bullet points.'''
        r = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role':'user','content':prompt}]
        )
        resume = r.choices[0].message.content
        session['resume'] = resume
        return redirect(url_for('result'))
    return render_template('builder.html')

@app.route('/result')
def result():
    return render_template('result.html', resume=session.get('resume',''))

@app.route('/pay')
def pay():
    checkout = stripe.checkout.Session.create(
        payment_method_types=['card'],
        mode='payment',
        line_items=[{
            'price_data': {
                'currency':'gbp',
                'product_data': {'name':'Premium Resume PDF'},
                'unit_amount':500
            },
            'quantity':1
        }],
        success_url=f'{BASE_URL}/download',
        cancel_url=f'{BASE_URL}/result'
    )
    return redirect(checkout.url, code=303)

@app.route('/resume-for-<job>')
def seo(job):
    clean_job_name = job.replace('-', ' ').title()
    return render_template('seo.html', job=clean_job_name)

@app.route('/resume')
def resume_index():
    return render_template('resume_index.html', roles=roles)

@app.route('/download')
def download():
    resume = session.get('resume', 'No resume found')
    html_content = f"<html><body>{resume}</body></html>"
    # Create a temporary PDF file
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    HTML(string=html_content).write_pdf(temp_pdf.name)
    return send_file(temp_pdf.name, as_attachment=True, download_name="resume.pdf")

if __name__ == "__main__":
    app.run(debug=True)