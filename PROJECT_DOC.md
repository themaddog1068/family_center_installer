# Family Center Installer - Project Documentation

## 🎯 Project Overview

This repository contains the installer for the Family Center application - a digital photo frame and slideshow system designed to run on Raspberry Pi devices. The project has evolved through multiple versions to address various challenges and improve the user experience.

## 📋 Project Goals

1. **Universal Installation**: Create a one-command installer that works on any Raspberry Pi
2. **Enhanced Configuration**: Provide a comprehensive web interface for slideshow configuration
3. **Google Drive Integration**: Enable photo synchronization from Google Drive
4. **Self-Contained**: Eliminate dependency on external repositories during installation
5. **User-Friendly**: Simple setup process with clear instructions

## 🚀 Version History

### Version 4 (Original)
- **Status**: ✅ Complete
- **Approach**: Cloned from private GitHub repository
- **Issues**: Required repository access, complex setup for private repos
- **Features**: Basic web interface, Google Drive sync

### Version -5 (Pre-Alpha) - Current
- **Status**: 🔄 In Development
- **Approach**: Self-contained installer with embedded application files
- **Goal**: No external repository dependencies
- **Features**: Enhanced web interface with full slideshow configuration

## 🔧 Technical Challenges & Solutions

### Challenge 1: Private Repository Access
**Problem**: Original installer failed with 404 errors when trying to clone private repository
**Solution**: Added interactive prompts for SSH keys or Personal Access Tokens

### Challenge 2: Heredoc Syntax Issues
**Problem**: Complex Python code embedded in bash heredocs caused syntax errors
**Solutions Attempted**:
- Fixed EOF delimiter placement
- Used unique delimiters (REQUIREMENTS_EOF, WEB_INTERFACE_EOF, etc.)
- Simplified embedded content

### Challenge 3: Enhanced Interface Dependencies
**Problem**: Enhanced web interface required heavy dependencies (playwright) not suitable for Pi
**Solution**: Created simplified versions of dependencies while maintaining full functionality

### Challenge 4: Installer Complexity
**Problem**: Embedding large amounts of code in installer made it unreliable
**Current Solution**: Package-based approach - download and extract application files

## 📁 Current Repository Structure

```
family_center_installer/
├── install.sh                    # Original universal installer (Version 4)
├── install_v-5.sh               # Current self-contained installer (Version -5)
├── test_install.sh              # Testing version of installer
├── README.md                    # Main documentation
├── PROJECT_DOC.md               # This file - project documentation
├── SETUP_GUIDE.md               # SSH/HTTPS setup instructions
├── family_center_enhanced_v5.zip # Enhanced application package
├── family_center_package/       # Source for the enhanced package
│   ├── src/
│   │   ├── main.py             # Main application entry point
│   │   ├── modules/
│   │   │   └── web_interface.py # Enhanced web interface
│   │   ├── config/
│   │   │   └── config_manager.py # Configuration management
│   │   └── services/
│   │       └── web_content_service.py # Simplified web content service
│   ├── requirements.txt         # Python dependencies
│   └── README.md               # Package documentation
├── enhanced_web_interface_simple.py # Simplified enhanced interface
├── config_manager.py           # Configuration manager
├── simple_web_content_service.py # Simplified web content service
└── sync_to_family_center.sh    # Script to sync improvements to main repo
```

## 🎨 Enhanced Interface Features

The enhanced web interface includes comprehensive configuration options:

### Slideshow Configuration
- ✅ **Slide Duration**: Control how long each slide is displayed
- ✅ **Shuffle**: Enable/disable random slide ordering
- ✅ **Transitions**: Enable smooth transitions between slides
- ✅ **Transition Types**: Crossfade, slide, zoom, fade, none
- ✅ **Transition Duration**: Control transition timing
- ✅ **Ease Types**: Linear, ease-in, ease-out, ease-in-out
- ✅ **Video Playback**: Enable/disable video support
- ✅ **Time-based Weighting**: Advanced media selection algorithms
- ✅ **Day of Week Weighting**: Weight media by day of week

### Folder Management
- ✅ **Google Drive Integration**: Configure Google Drive folder ID
- ✅ **Local Media Paths**: Set local media directories
- ✅ **Auto-sync**: Enable automatic synchronization
- ✅ **Sync Intervals**: Configure sync frequency

### Credential Management
- ✅ **Web-based Upload**: Upload credentials through web interface
- ✅ **Credential Status**: View current credential files
- ✅ **Setup Instructions**: Step-by-step credential setup guide

### System Configuration
- ✅ **Web Interface Settings**: Host, port, debug mode
- ✅ **Configuration Display**: View current settings
- ✅ **Real-time Updates**: Save configuration changes

## 🔄 Current Development Status

### ✅ Completed
- [x] Original installer with private repo handling
- [x] Enhanced web interface development
- [x] Simplified dependency management
- [x] Package-based installer approach
- [x] Comprehensive slideshow configuration
- [x] Credential management interface
- [x] System configuration options

### 🔄 In Progress
- [x] Package-based installer created and tested
- [x] Enhanced interface included in package
- [x] Service creation and startup working
- [ ] **CURRENT ISSUE**: Missing config module files causing import errors
- [ ] **NEXT**: Complete missing config files and test service startup
- [ ] Documentation updates

### 📋 Next Steps
- [x] Test installer on fresh Pi installation
- [ ] **IMMEDIATE**: Fix missing config module files
  - [ ] Copy `src/config/__init__.py` (Config class)
  - [ ] Copy `src/config/environment.py` 
  - [ ] Copy `src/config/logging_config.py`
  - [ ] Copy `src/config/config.yaml` (default config)
- [ ] **NEXT**: Test service startup with complete config
- [ ] **THEN**: Validate enhanced interface loads correctly
- [ ] Create user guide for enhanced features
- [ ] Optimize package size and download speed
- [ ] Add error handling and recovery options

## 🐛 Known Issues

### Installer Issues
1. **Heredoc Complexity**: Embedding large Python files in bash scripts causes reliability issues
   - **Status**: 🔄 Being addressed with package-based approach
   - **Impact**: High - affects installer reliability

2. **Dependency Conflicts**: Heavy dependencies not suitable for Pi
   - **Status**: ✅ Resolved with simplified services
   - **Impact**: Medium - affects functionality

### Interface Issues
1. **UI Expectations**: User expects specific enhanced interface features
   - **Status**: ✅ Addressed with comprehensive configuration options
   - **Impact**: High - affects user satisfaction

## 🛠️ Development Approach

### Package-Based Installation
**Current Strategy**: Instead of embedding all code in the installer:
1. Create a complete application package
2. Host package on GitHub
3. Download and extract during installation
4. Install Python dependencies
5. Configure system service

**Benefits**:
- ✅ Eliminates heredoc issues
- ✅ Makes installer more reliable
- ✅ Easier to update application
- ✅ Cleaner separation of concerns
- ✅ Better maintainability

### Simplified Dependencies
**Strategy**: Create lightweight versions of heavy dependencies:
- `simple_web_content_service.py` instead of full playwright-based service
- Maintain same interface for compatibility
- Focus on configuration rather than heavy processing

## 📊 Testing Status

### Installer Testing
- [x] Local development environment
- [x] Basic functionality validation
- [ ] Raspberry Pi deployment
- [ ] Fresh Pi installation
- [ ] Upgrade from previous versions

### Interface Testing
- [x] Local web interface
- [x] Configuration saving/loading
- [x] Credential management
- [ ] Pi deployment testing
- [ ] User acceptance testing

## 🎯 Success Criteria

### Version -5 Success Metrics
- [ ] One-command installation works on fresh Pi
- [ ] Enhanced interface loads with all features
- [ ] Slideshow configuration saves correctly
- [ ] Google Drive credentials can be added
- [ ] Service starts automatically on boot
- [ ] No external repository dependencies during install

### User Experience Goals
- [ ] Installation completes in under 5 minutes
- [ ] Web interface is intuitive and comprehensive
- [ ] All configuration options are accessible
- [ ] Clear error messages and recovery options
- [ ] Minimal manual intervention required

## 📚 Documentation Status

### ✅ Completed Documentation
- [x] Main README with installation instructions
- [x] SSH/HTTPS setup guide
- [x] Project documentation (this file)
- [x] Package documentation
- [x] API documentation

### 📋 Planned Documentation
- [ ] User guide for enhanced features
- [ ] Troubleshooting guide
- [ ] Development setup guide
- [ ] Contributing guidelines

## 🔗 Related Repositories

- **Main Application**: `family_center` (private) - Contains the full application with all features
- **Credentials**: `family_center_credentials` (private) - Contains Google Drive credentials
- **This Repository**: `family_center_installer` (public) - Contains installers and documentation

## 👥 Team & Contributions

- **Primary Developer**: Benjamin Hodson
- **Repository Owner**: themaddog1068
- **Testing**: Raspberry Pi deployment testing

## 📞 Support & Communication

- **Issues**: GitHub Issues in this repository
- **Documentation**: This file and README.md
- **Updates**: Git commits and releases

---

**Last Updated**: December 2024
**Version**: -5 (Pre-Alpha)
**Status**: Active Development

## 🚨 **CURRENT STATUS - END OF DAY**

### ✅ **What's Working:**
- Package-based installer downloads and extracts successfully
- All application files are included in the package
- Service creation and systemd setup works
- Enhanced web interface is included in the package

### 🚨 **Current Issue:**
- **Service fails to start** due to missing config module files
- **Error**: `ModuleNotFoundError: No module named 'src.config'`
- **Root Cause**: Missing `src/config/__init__.py` file that exports the `Config` class

### 📋 **Tomorrow's Tasks:**
1. **Copy missing config files** from family-center main branch:
   - `src/config/__init__.py` (contains Config class)
   - `src/config/environment.py`
   - `src/config/logging_config.py`
   - `src/config/config.yaml` (default configuration)

2. **Create new package** with complete config files

3. **Test service startup** on Pi

4. **Verify enhanced interface** loads correctly

### 🎯 **Expected Outcome:**
Once config files are included, the service should start successfully and provide the enhanced web interface with all slideshow configuration options. 