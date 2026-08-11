cmake_minimum_required(VERSION 3.8)
project(nana_v3_description)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

foreach(install_dir assets launch rviz scripts urdf)
  if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${install_dir}")
    install(DIRECTORY ${install_dir} DESTINATION share/${PROJECT_NAME})
  endif()
endforeach()

ament_package()
