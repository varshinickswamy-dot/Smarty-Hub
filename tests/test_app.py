import os
import tempfile
import unittest

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["APP_ENV"] = "development"

import app as app_module
from app import app, db
from models import User


class SmartyHubAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output_dir = tempfile.TemporaryDirectory()
        app_module.REPORT_FOLDER = cls.output_dir.name

    @classmethod
    def tearDownClass(cls):
        cls.output_dir.cleanup()

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        with app.app_context():
            db.drop_all()
            db.create_all()

    def register_and_login(self):
        self.client.post(
            "/register",
            data={"name": "Test Student", "email": "student@example.test", "password": "test-password"},
        )
        return self.client.post(
            "/",
            data={"email": "student@example.test", "password": "test-password"},
        )

    def test_registration_login_and_career_recommendation(self):
        response = self.register_and_login()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/dashboard").status_code, 200)

        response = self.client.post("/career", data={"stream": "science", "marks": "85"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Medical (MBBS)", response.data)

    def test_invalid_career_input_is_rejected(self):
        self.register_and_login()
        response = self.client.post("/career", data={"stream": "unknown", "marks": "101"})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"valid stream", response.data)

    def test_chat_endpoint_validates_payload_and_replies(self):
        self.register_and_login()

        invalid_response = self.client.post("/chat", json={"msg": ""})
        self.assertEqual(invalid_response.status_code, 400)

        response = self.client.post("/chat", json={"msg": "Tell me about engineering"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Engineering", response.get_json()["reply"])

    def test_resume_route_generates_pdf_with_user_text(self):
        self.register_and_login()
        response = self.client.post(
            "/resume",
            data={
                "name": "<Test Student>",
                "email": "student@example.test",
                "summary": "Builds <useful> things & learns.",
                "skills": "Python, SQL",
            },
        )

        self.assertEqual(response.status_code, 303)
        self.assertIn("/resume/download/1", response.headers["Location"])
        response = self.client.get(response.headers["Location"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/pdf")
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertIn("SmartyHub_Resume_1.pdf", response.headers["Content-Disposition"])
        self.assertTrue(response.data.startswith(b"%PDF"))
        response.close()
        with app.app_context():
            self.assertEqual(User.query.count(), 1)


    def test_launchpad_requires_login_and_builds_action_plan(self):
        response = self.client.get("/launchpad")
        self.assertEqual(response.status_code, 302)
        self.register_and_login()
        response = self.client.post(
            "/launchpad",
            data={
                "skills": "Python, SQL, communication",
                "interests": "AI and machine learning",
                "goal": "Build a portfolio project",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your 4-step proof sprint", response.data)
        self.assertIn(b"Build an intelligent solution", response.data)
        self.assertIn(b"portfolio project", response.data.lower())


    def test_career_lab_requires_login_and_supports_resume_and_interview(self):
        self.assertEqual(self.client.get("/career-lab").status_code, 302)
        self.register_and_login()
        ats = self.client.post(
            "/career-lab",
            data={
                "action": "ats",
                "target_role": "Software Developer",
                "resume_text": "Built Python and SQL projects with Git. Developed APIs and testing workflows.",
            },
        )
        self.assertEqual(ats.status_code, 200)
        self.assertIn(b"Your resume snapshot", ats.data)
        interview = self.client.post(
            "/career-lab",
            data={"action": "interview", "interview_role": "Software Developer"},
        )
        self.assertEqual(interview.status_code, 200)
        self.assertIn(b"Practice round", interview.data)
        self.assertIn(b"debug an API", interview.data)

    def test_timetable_and_admin_pages_render_for_admin(self):
        self.register_and_login()
        with app.app_context():
            user = User.query.filter_by(email="student@example.test").first()
            user.role = "admin"
            db.session.commit()

        self.assertEqual(self.client.get("/timetable").status_code, 200)
        admin_response = self.client.get("/admin")
        self.assertEqual(admin_response.status_code, 200)
        self.assertIn(b'table-responsive', admin_response.data)


if __name__ == "__main__":
    unittest.main()
