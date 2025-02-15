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
    }
  ]
}