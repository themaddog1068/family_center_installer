# Python Project Template

A modern, production-ready Python project template following best practices for development, testing, and deployment.

## 🌟 Features

- Modern Python project structure
- Comprehensive testing setup with pytest
- Code quality tools (black, ruff, mypy)
- Pre-commit hooks for code quality
- GitHub Actions CI/CD pipeline
- Type checking support
- Documentation structure
- Development environment setup

## 📋 Prerequisites

- Python 3.8+
- pip package manager
- Virtual environment (recommended)
- Git

## 🚀 Getting Started

1. Use this template to create a new repository or clone it:
   ```bash
   git clone <your-repo-url>
   cd <your-project-name>
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

5. Run the tests:
   ```bash
   pytest
   ```

6. Start developing:
   ```bash
   python src/main.py
   ```

## 🏗️ Project Structure

```
your-project/
├── src/                    # Source code
│   ├── your_package/      # Main package
│   └── main.py           # Entry point
├── tests/                 # Test suite
├── docs/                  # Documentation
├── .github/               # GitHub workflows and templates
├── .cursor/               # Cursor IDE configurations
├── pyproject.toml         # Project configuration and dependencies
├── requirements.txt       # Project dependencies
└── README.md             # This file
```

## 🧪 Testing

We use pytest for our testing framework. Run tests with:

```bash
pytest
```

For coverage report:

```bash
pytest --cov=src tests/
```

## 📚 Documentation

Detailed documentation is available in the `docs/` directory:

- [Setup Guide](docs/setup.md)
- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Contributing Guide](docs/contributing.md)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 Code Quality

This template enforces code quality through:

- **black**: Code formatting
- **ruff**: Fast linting and formatting
- **isort**: Import sorting
- **mypy**: Type checking
- **pre-commit**: Automated quality checks

Run quality checks manually:
```bash
black src tests
ruff check src tests
mypy src
```

## 🔧 Development Tools

### Cursor IDE Support
This template includes Cursor IDE configurations in `.cursor/` for optimal development experience.

### Pre-commit Hooks
Automatically run code quality checks before commits:
```bash
pre-commit run --all-files
```

### Continuous Integration
GitHub Actions workflow automatically:
- Runs tests across multiple Python versions
- Checks code quality
- Builds the package
- Uploads coverage reports

## 🚀 Deployment

Build the package:
```bash
python -m build
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎯 Next Steps

After using this template:

1. Update `pyproject.toml` with your project details
2. Replace this README with your project-specific content
3. Add your source code to `src/your_package/`
4. Write tests in the `tests/` directory
5. Update documentation in `docs/`
6. Configure any additional CI/CD requirements

## Credentials Management

Credentials and service account files are stored in a separate directory outside the repository for security reasons. The credentials directory is located at `../family_center_credentials/` relative to the project root. This directory contains:

- `service-account.json`: Google Drive service account credentials
- `calendar-service-account.json`: Google Calendar service account credentials
- `credentials.json`: OAuth 2.0 client credentials

To set up the project:

1. Create a `credentials` directory in the project root
2. Create symbolic links to the credentials files:
   ```bash
   ln -s ../family_center_credentials/service-account.json credentials/
   ln -s ../family_center_credentials/calendar-service-account.json credentials/
   ln -s ../family_center_credentials/credentials.json credentials/
   ```
