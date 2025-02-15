module.exports = {
  apps: [
    {
      name: "lords",
      script: "lords.py",
      interpreter: "venv/bin/python3",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      env: {
        NODE_ENV: "production",
        PORT: "8000"
      },
      error_file: "logs/lords-error.log",
      out_file: "logs/lords-out.log"
    },
    {
      name: "lords-unique",
      script: "lords_unique.py",
      interpreter: "venv/bin/python3",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      env: {
        NODE_ENV: "production",
        PORT: "8001"
      },
      error_file: "logs/lords-unique-error.log",
      out_file: "logs/lords-unique-out.log"
    },
    {
      name: "packs",
      script: "packs.py",
      interpreter: "venv/bin/python3",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      env: {
        NODE_ENV: "production",
        PORT: "8002"
      },
      error_file: "logs/packs-error.log",
      out_file: "logs/packs-out.log"
    },
    {
      name: "packs-unique",
      script: "packs_unique.py",
      interpreter: "venv/bin/python3",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      env: {
        NODE_ENV: "production",
        PORT: "8003"
      },
      error_file: "logs/packs-unique-error.log",
      out_file: "logs/packs-unique-out.log"
    },
    {
      name: "units",
      script: "units.py",
      interpreter: "venv/bin/python3",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      env: {
        NODE_ENV: "production",
        PORT: "8004"
      },
      error_file: "logs/units-error.log",
      out_file: "logs/units-out.log"
    },
    {
      name: "units-unique",
      script: "units_unique.py",
      interpreter: "venv/bin/python3",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      env: {
        NODE_ENV: "production",
        PORT: "8005"
      },
      error_file: "logs/units-unique-error.log",
      out_file: "logs/units-unique-out.log"
    },
    {
      name: "skins",
      script: "skins.py",
      interpreter: "venv/bin/python3",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      env: {
        NODE_ENV: "production",
        PORT: "8006"
      },
      error_file: "logs/skins-error.log",
      out_file: "logs/skins-out.log"
    },
    {
      name: "skins-unique",
      script: "skins_unique.py",
      interpreter: "venv/bin/python3",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      env: {
        NODE_ENV: "production",
        PORT: "8007"
      },
      error_file: "logs/skins-unique-error.log",
      out_file: "logs/skins-unique-out.log"
    },
    {
      name: "timestamps",
      script: "timestamps.py",
      interpreter: "venv/bin/python3",
      autorestart: true,
      watch: false,
      max_memory_restart: "1G",
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      env: {
        NODE_ENV: "production",
        PORT: "8008"
      },
      error_file: "logs/timestamps-error.log",
      out_file: "logs/timestamps-out.log"
    }
  ]
}