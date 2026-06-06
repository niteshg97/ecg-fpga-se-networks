#ifndef DEFINES_H_
#define DEFINES_H_

#include "ap_fixed.h"
#include "ap_int.h"
#include "nnet_utils/nnet_types.h"
#include <array>
#include <cstddef>
#include <cstdio>
#include <tuple>
#include <tuple>


// hls-fpga-machine-learning insert numbers

// hls-fpga-machine-learning insert layer-precision
typedef ap_fixed<12,6> input_t;
typedef ap_fixed<12,6> model_default_t;
typedef ap_fixed<25,13> embedding_result_t;
typedef ap_fixed<12,6> embedding_weight_t;
typedef ap_fixed<12,6> embedding_bias_t;
typedef ap_fixed<12,6> layer5_t;
typedef ap_fixed<18,8> emb_relu_table_t;
typedef ap_fixed<29,17> ffn1_result_t;
typedef ap_fixed<12,6> ffn1_weight_t;
typedef ap_fixed<12,6> ffn1_bias_t;
typedef ap_fixed<12,6> layer9_t;
typedef ap_fixed<18,8> ffn_relu_table_t;
typedef ap_fixed<30,18> ffn2_result_t;
typedef ap_fixed<12,6> ffn2_weight_t;
typedef ap_fixed<12,6> ffn2_bias_t;
typedef ap_fixed<31,19> ffn_add_result_t;
typedef ap_fixed<44,26> final_bn_result_t;
typedef ap_fixed<12,6> final_bn_scale_t;
typedef ap_fixed<12,6> final_bn_bias_t;
typedef ap_fixed<12,6> layer14_t;
typedef ap_fixed<29,17> se_dense1_result_t;
typedef ap_fixed<12,6> se_dense1_weight_t;
typedef ap_fixed<12,6> se_dense1_bias_t;
typedef ap_uint<1> layer15_index;
typedef ap_fixed<12,6> layer16_t;
typedef ap_fixed<18,8> se_dense1_relu_table_t;
typedef ap_fixed<28,16> se_dense2_result_t;
typedef ap_fixed<12,6> se_dense2_weight_t;
typedef ap_fixed<12,6> se_dense2_bias_t;
typedef ap_uint<1> layer17_index;
typedef ap_fixed<12,6> layer18_t;
typedef ap_fixed<18,8> se_dense2_sigmoid_table_t;
typedef ap_fixed<24,12> se_mult_result_t;
typedef ap_fixed<25,13> se_add_result_t;
typedef ap_fixed<42,24> result_t;
typedef ap_fixed<12,6> output_logits_weight_t;
typedef ap_fixed<12,6> output_logits_bias_t;
typedef ap_uint<1> layer21_index;

// hls-fpga-machine-learning insert emulator-defines


#endif
