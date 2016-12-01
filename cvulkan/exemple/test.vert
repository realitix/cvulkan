#version 450
#extension GL_ARB_separate_shader_objects : enable

out gl_PerVertex {
    vec4 gl_Position;
};

const bool success = false;
float x;



    if(x) {
const float NORMAL_MAP = 2.0;
x = NORMAL_MAP;
}
else {
x = 0.0;
}

void main() {
    gl_Position = vec4(x, 0.0, 0.0, 1.0);
}

