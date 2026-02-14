from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from tenants.models import Tenant

class TenantViewsTest(TestCase):
    def test_home_page(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'tenants/home.html')

    def test_register_creates_user_and_tenant(self):
        url = reverse('register')
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'tenant_name': 'Test Organization'
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse('tenant-dashboard'))

        # Verify User created
        user = User.objects.get(username='testuser')
        self.assertTrue(user.check_password('password123'))

        # Verify Tenant created
        tenant = Tenant.objects.get(user=user)
        self.assertEqual(tenant.name, 'Test Organization')
        self.assertEqual(tenant.slug, 'test-organization')

    def test_register_duplicate_tenant_name(self):
        # Create a tenant first
        user = User.objects.create_user(username='user1', password='password')
        Tenant.objects.create(user=user, name='Test Organization', slug='test-organization')

        url = reverse('register')
        data = {
            'username': 'user2',
            'email': 'user2@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'tenant_name': 'Test Organization' # Same name
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)

        # Verify form errors
        form = response.context['form']
        self.assertTrue(form.errors)
        self.assertIn('Tenant with this name already exists (slug conflict).', form.errors['tenant_name'])

    def test_authenticated_user_redirect_from_register(self):
        user = User.objects.create_user(username='user1', password='password')
        # Create a tenant for the user to avoid dashboard error
        Tenant.objects.create(user=user, name='User1 Tenant', slug='user1-tenant')

        self.client.force_login(user)
        response = self.client.get(reverse('register'))
        self.assertRedirects(response, reverse('tenant-dashboard'))
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


class LogoutViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="carol", password="password123")
        Tenant.objects.create(user=self.user, name="Carol Tenant", slug="carol-tenant")

    def test_logout_logs_user_out(self):
        self.client.login(username="carol", password="password123")
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))
