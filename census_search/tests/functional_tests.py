from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import unittest


class NewSearchTest(unittest.TestCase):
	def setUp(self):
		self.browser = webdriver.Firefox()
		self.browser.implicitly_wait(3)

	def tearDown(self):
		self.browser.quit()

	def test_city_selection(self):
		# Search page
		self.browser.get('http://localhost:8000/search')

		# User notices the Search bar...
		self.assertIn('Census data', self.browser.title)
		search_text = self.browser.find_element_by_tag_name('label').text
		self.assertIn('Places:', search_text)

		# User enters something in the Search bar
		place_input = self.browser.find_element_by_id('places')
		place_input.send_keys('Cudahy,WI')

		# User clicks View
		link = self.browser.find_element_by_link_text('View')
		link.click()


if __name__ == '__main__':
	unittest.main(warnings='ignore')