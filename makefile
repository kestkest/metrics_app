start:
	docker-compose up -d app_db migrator
	sleep 1
	docker-compose up -d app metrics_loader
