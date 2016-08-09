import unittest
from selenium import webdriver

# assert 'Search test' in browser.title, "Browser title was " + browser.title

class NewVisitorTest(unittest.TestCase):
	def setUp(self):
		self.browser = webdriver.Firefox()
		self.browser.implicitly_wait(3)

	def tearDown(self):
		self.browser.quit()

	def test_city_selection(self):
		# Search
		# homepage
		self.browser.get('http://localhost:8000/search')

		# User notices the page title and header...
		self.assertIn('Census data', self.browser.title)
		self.fail('Finish the test!')



if __name__ == '__main__':
	unittest.main(warnings='ignore')