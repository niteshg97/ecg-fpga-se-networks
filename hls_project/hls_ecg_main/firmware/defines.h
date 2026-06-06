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
typedef ap_fixed<24,12> input_t;
typedef ap_fixed<24,12> model_default_t;
typedef ap_fixed<49,25> embedding_result_t;
typedef ap_fixed<24,12> embedding_weight_t;
typedef ap_fixed<24,12> embedding_bias_t;
typedef ap_fixed<24,12> layer5_t;
typedef ap_fixed<18,8> emb_relu_table_t;
typedef ap_fixed<53,29> ffn1_result_t;
typedef ap_fixed<24,12> ffn1_weight_t;
typedef ap_fixed<24,12> ffn1_bias_t;
typedef ap_fixed<24,12> layer9_t;
typedef ap_fixed<18,8> ffn_relu_table_t;
typedef ap_fixed<54,30> ffn2_result_t;
typedef ap_fixed<24,12> ffn2_weight_t;
typedef ap_fixed<24,12> ffn2_bias_t;
typedef ap_fixed<55,31> ffn_add_result_t;
typedef ap_fixed<80,44> final_bn_result_t;
typedef ap_fixed<24,12> final_bn_scale_t;
typedef ap_fixed<24,12> final_bn_bias_t;
typedef ap_fixed<24,12> layer14_t;
typedef ap_fixed<53,29> se_dense1_result_t;
typedef ap_fixed<24,12> se_dense1_weight_t;
typedef ap_fixed<24,12> se_dense1_bias_t;
typedef ap_uint<1> layer15_index;
typedef ap_fixed<24,12> layer16_t;
typedef ap_fixed<18,8> se_dense1_relu_table_t;
typedef ap_fixed<52,28> se_dense2_result_t;
typedef ap_fixed<24,12> se_dense2_weight_t;
typedef ap_fixed<24,12> se_dense2_bias_t;
typedef ap_uint<1> layer17_index;
typedef ap_fixed<24,12> layer18_t;
typedef ap_fixed<18,8> se_dense2_sigmoid_table_t;
typedef ap_fixed<48,24> se_mult_result_t;
typedef ap_fixed<49,25> se_add_result_t;
typedef ap_fixed<78,42> result_t;
typedef ap_fixed<24,12> output_logits_weight_t;
typedef ap_fixed<24,12> output_logits_bias_t;
typedef ap_uint<1> layer21_index;

// hls-fpga-machine-learning insert emulator-defines


#endif
