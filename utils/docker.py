import re
import docker
from utils.logger import log
from __init__ import __version__

docker_client = None


def _strip_scheme(value):
	"""Remove URL schemes like https:// from registry/image strings."""
	if not value:
		return ""
	value = value.strip()
	return re.sub(r'^[a-zA-Z]+://', '', value)


def sanitize_registry(registry):
	"""Normalize registry strings (strip schemes/trailing slashes)."""
	registry = _strip_scheme(registry)
	return registry.rstrip('/')


def sanitize_image_reference(image_name):
	"""Normalize image references by stripping schemes and duplicate slashes."""
	image_name = _strip_scheme(image_name)
	if not image_name:
		return ""
	return re.sub(r'/+', '/', image_name)


def build_full_image_name(registry, image_name):
	"""Combine registry and image name safely, avoiding schemes and duplicates."""
	image_name = sanitize_image_reference(image_name)
	registry = sanitize_registry(registry)
	if registry:
		if image_name.startswith(f"{registry}/"):
			return image_name
		return f"{registry}/{image_name}" if image_name else registry
	return image_name

def init_docker():
	global docker_client
	
	if docker_client is not None:
		return docker_client
		
	try:
		docker_client = docker.DockerClient(base_url="unix:///var/run/docker.sock")
		docker_client.ping()
  
		return docker_client
		
	except Exception as e:
		print(f"Docker connection failed: {str(e)}")
		docker_client = None
		return None

def is_docker_available():
	"""Return True if the Docker client is initialized and working"""
	return docker_client is not None

def get_docker_version():
	"""Return Docker version or error message if not available"""
	if not docker_client:
		return "Docker not available"
	
	try:
		return docker_client.version()["Version"]
	except Exception as e:
		return f"Error: {str(e)}"

def cleanup_containers():
	"""Delete any existing hostlife containers"""
	if not docker_client:
		print("No Docker client available, skipping container cleanup")
		return
		
	try:
		containers = docker_client.containers.list(all=True)
		for container in containers:
			regex = re.compile(r"hostlife_generated_([a-z0-9]+(-[a-z0-9]+)+)", re.IGNORECASE)
			if regex.match(container.name):
				print(f"Stopping container {container.name}")
				try:
					container.stop()
					container.remove()
				except Exception as e:
					print(f"Error stopping container {container.name}: {str(e)}")
	except Exception as e:
		print(f"Error listing containers: {str(e)}")

def force_pull_required_images():
	"""Force pull all required images for hostlife (called during startup)"""
	if not docker_client:
		print("No Docker client available, skipping required image pull")
		return
		
	try:
		log("INFO", "Starting required image pull for hostlife...")
		
		# Define all required images for hostlife
		required_images = [
			# Guacamole image (always required)
			{
				"name": f"ghcr.io/zwpseudo/hostlife-guac:{__version__}",
				"description": "Guacamole VNC Server"
			}
		]
		
		# Add droplet images from database
		from models.droplet import Droplet
		droplets = Droplet.query.all()
		for droplet in droplets:
			if droplet.container_docker_image is None:
				continue
			
			image = build_full_image_name(droplet.container_docker_registry, droplet.container_docker_image)
			if not image:
				continue
			
			required_images.append({
				"name": image,
				"description": f"Droplet: {droplet.display_name}"
			})

		# Pull all required images
		for img_info in required_images:
			image_name = img_info["name"]
			description = img_info["description"]
			
			log("INFO", f"Pulling required Docker image {image_name} ({description})")
			try:
				# Extract tag from image name - handle multiple colons properly
				if ":" in image_name:
					# Split on last colon to handle image names with multiple colons
					parts = image_name.rsplit(":", 1)
					base_image = parts[0]
					tag = parts[1]
				else:
					base_image = image_name
					tag = "latest"
				
				docker_client.images.pull(base_image, tag)
				log("INFO", f"Successfully pulled required Docker image {image_name} ({description})")
			except Exception as e:
				log("ERROR", f"Error pulling required Docker image {image_name} ({description}): {e}")
				
		log("INFO", "Required image pull for hostlife completed")
				
	except Exception as e:
		log("ERROR", f"Error in force_pull_required_images: {str(e)}")

def pull_images():
	"""Pull all required docker images for hostlife"""
	if not docker_client:
		print("No Docker client available, skipping image pull")
		return
		
	from models.droplet import Droplet
	
	try:
		# Define all required images for hostlife
		required_images = [
			# Guacamole image (always required)
			{
				"name": f"ghcr.io/zwpseudo/hostlife-guac:{__version__}",
				"description": "Guacamole VNC Server"
			}
		]
		
		# Add droplet images from database
		droplets = Droplet.query.all()
		for droplet in droplets:
			if droplet.container_docker_image is None:
				continue
		
			image = build_full_image_name(droplet.container_docker_registry, droplet.container_docker_image)
			if not image:
				continue
		
			required_images.append({
				"name": image,
				"description": f"Droplet: {droplet.display_name}"
			})

		# Pull all required images
		for img_info in required_images:
			image_name = img_info["name"]
			description = img_info["description"]
			
			log("INFO", f"Pulling required Docker image {image_name} ({description})")
			try:
				# Extract tag from image name - handle multiple colons properly
				if ":" in image_name:
					# Split on last colon to handle image names with multiple colons
					parts = image_name.rsplit(":", 1)
					base_image = parts[0]
					tag = parts[1]
				else:
					base_image = image_name
					tag = "latest"
				
				docker_client.images.pull(base_image, tag)
				log("INFO", f"Successfully pulled required Docker image {image_name} ({description})")
			except Exception as e:
				log("ERROR", f"Error pulling required Docker image {image_name} ({description}): {e}")
				
		log("INFO", "Required image pull for hostlife completed")
				
	except Exception as e:
		log("ERROR", f"Error in pull_images: {str(e)}")

def check_image_exists(registry, image_name):
	"""Check if a Docker image exists locally"""
	if not docker_client:
		return False
	
	try:
		full_image = build_full_image_name(registry, image_name)
			
		# Check if image exists locally
		images = docker_client.images.list()
		for image in images:
			if full_image in image.tags:
				return True
		return False
	except Exception as e:
		log("ERROR", f"Error checking if image exists: {str(e)}")
		return False

def pull_single_image(registry, image_name):
	"""Pull a single Docker image and return success status and message"""
	if not docker_client:
		return False, "Docker client not available"
	
	try:
		# Validate image name is not empty
		if not image_name or not image_name.strip():
			return False, "Image name cannot be empty"
		
		full_image = build_full_image_name(registry, image_name)
			
		# Extract tag from image name - handle multiple colons properly
		if ":" in full_image:
			# Split on last colon to handle image names with multiple colons
			parts = full_image.rsplit(":", 1)
			repository = parts[0]
			tag = parts[1]
		else:
			repository = full_image
			tag = "latest"
		
		log("INFO", f"Manually pulling Docker image {full_image}")
		docker_client.images.pull(repository, tag)
		log("INFO", f"Successfully pulled Docker image {full_image}")
		return True, f"Successfully pulled {full_image}"
		
	except Exception as e:
		error_msg = f"Error pulling Docker image {image_name}: {str(e)}"
		log("ERROR", error_msg)
		return False, error_msg

def get_images_status():
	"""Get status of all required images (downloaded/missing)"""
	if not docker_client:
		return {}
	
	try:
		from models.droplet import Droplet
		
		# Define all required images
		required_images = [
			{
				"id": "guac",
				"name": "Guacamole",
				"image": f"ghcr.io/zwpseudo/hostlife-guac:{__version__}",
				"description": "Guacamole VNC Server"
			}
		]
		
		# Add droplet images from database
		droplets = Droplet.query.all()
		for droplet in droplets:
			if droplet.container_docker_image is None:
				continue
			
			full_image = build_full_image_name(droplet.container_docker_registry, droplet.container_docker_image)
			if not full_image:
				continue
			
			required_images.append({
				"id": droplet.id,
				"name": droplet.display_name,
				"image": full_image,
				"description": f"Droplet: {droplet.display_name}"
			})
		
		status = {}
		local_images = docker_client.images.list()
		local_image_tags = []
		for image in local_images:
			local_image_tags.extend(image.tags)
		
		for img_info in required_images:
			# Check if image exists locally using exact match instead of substring
			exists = any(img_info["image"] == tag for tag in local_image_tags)
			
			status[img_info["id"]] = {
				"droplet_name": img_info["name"],
				"image": img_info["image"],
				"exists": exists,
				"description": img_info["description"]
			}
			
		return status
		
	except Exception as e:
		log("ERROR", f"Error getting images status: {str(e)}")
		return {}