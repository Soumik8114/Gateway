from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from tenants.models import Tenant


class LoginViewRedirectTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username="alice", password="password123")
		Tenant.objects.create(user=self.user, name="Alice Tenant", slug="alice-tenant")

	def test_login_page_accessible_when_logged_out(self):
		response = self.client.get(reverse("login"))
		self.assertEqual(response.status_code, 200)

	def test_logged_in_user_is_redirected_away_from_login(self):
		self.client.login(username="alice", password="password123")
		response = self.client.get(reverse("login"))
		self.assertRedirects(response, reverse("tenant-dashboard"))


class MyApisViewTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(username="bob", password="password123")
		Tenant.objects.create(user=self.user, name="Bob Tenant", slug="bob-tenant")

	def test_my_apis_requires_login(self):
		response = self.client.get(reverse("my-apis"))
		self.assertEqual(response.status_code, 302)

	def test_my_apis_page_loads_when_logged_in(self):
		self.client.login(username="bob", password="password123")
		response = self.client.get(reverse("my-apis"))
		self.assertEqual(response.status_code, 200)
