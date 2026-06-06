#include <iostream>

#include "myproject.h"
#include "parameters.h"


void myproject(
    input_t ecg_input[140*1],
    result_t layer21_out[2]
) {

    // hls-fpga-machine-learning insert IO
    #pragma HLS ARRAY_RESHAPE variable=ecg_input complete dim=0
    #pragma HLS ARRAY_PARTITION variable=layer21_out complete dim=0
    #pragma HLS INTERFACE ap_vld port=ecg_input,layer21_out 
    #pragma HLS DATAFLOW

    // hls-fpga-machine-learning insert load weights
#ifndef __SYNTHESIS__
    static bool loaded_weights = false;
    if (!loaded_weights) {
        nnet::load_weights_from_txt<embedding_weight_t, 16>(w23, "w23.txt");
        nnet::load_weights_from_txt<embedding_bias_t, 16>(b23, "b23.txt");
        nnet::load_weights_from_txt<ffn1_weight_t, 512>(w24, "w24.txt");
        nnet::load_weights_from_txt<ffn1_bias_t, 32>(b24, "b24.txt");
        nnet::load_weights_from_txt<ffn2_weight_t, 512>(w25, "w25.txt");
        nnet::load_weights_from_txt<ffn2_bias_t, 16>(b25, "b25.txt");
        nnet::load_weights_from_txt<final_bn_scale_t, 16>(s13, "s13.txt");
        nnet::load_weights_from_txt<final_bn_bias_t, 16>(b13, "b13.txt");
        nnet::load_weights_from_txt<se_dense1_weight_t, 128>(w15, "w15.txt");
        nnet::load_weights_from_txt<se_dense1_bias_t, 8>(b15, "b15.txt");
        nnet::load_weights_from_txt<se_dense2_weight_t, 128>(w17, "w17.txt");
        nnet::load_weights_from_txt<se_dense2_bias_t, 16>(b17, "b17.txt");
        nnet::load_weights_from_txt<output_logits_weight_t, 32>(w21, "w21.txt");
        nnet::load_weights_from_txt<output_logits_bias_t, 2>(b21, "b21.txt");
        loaded_weights = true;    }
#endif
    // ****************************************
    // NETWORK INSTANTIATION
    // ****************************************

    // hls-fpga-machine-learning insert layers

    embedding_result_t layer23_out[140*16];
    #pragma HLS ARRAY_PARTITION variable=layer23_out complete dim=0

    layer5_t layer5_out[140*16];
    #pragma HLS ARRAY_PARTITION variable=layer5_out complete dim=0

    ffn1_result_t layer24_out[140*32];
    #pragma HLS ARRAY_PARTITION variable=layer24_out complete dim=0

    layer9_t layer9_out[140*32];
    #pragma HLS ARRAY_PARTITION variable=layer9_out complete dim=0

    ffn2_result_t layer25_out[140*16];
    #pragma HLS ARRAY_PARTITION variable=layer25_out complete dim=0

    ffn_add_result_t layer12_out[140*16];
    #pragma HLS ARRAY_PARTITION variable=layer12_out complete dim=0

    final_bn_result_t layer13_out[140*16];
    #pragma HLS ARRAY_PARTITION variable=layer13_out complete dim=0

    layer14_t layer14_out[16];
    #pragma HLS ARRAY_PARTITION variable=layer14_out complete dim=0

    se_dense1_result_t layer15_out[8];
    #pragma HLS ARRAY_PARTITION variable=layer15_out complete dim=0

    layer16_t layer16_out[8];
    #pragma HLS ARRAY_PARTITION variable=layer16_out complete dim=0

    se_dense2_result_t layer17_out[16];
    #pragma HLS ARRAY_PARTITION variable=layer17_out complete dim=0

    layer18_t layer18_out[16];
    #pragma HLS ARRAY_PARTITION variable=layer18_out complete dim=0

    se_mult_result_t layer19_out[16];
    #pragma HLS ARRAY_PARTITION variable=layer19_out complete dim=0

    se_add_result_t layer20_out[16];
    #pragma HLS ARRAY_PARTITION variable=layer20_out complete dim=0

    nnet::pointwise_conv_1d_cl<input_t, embedding_result_t, config26>(ecg_input, layer23_out, w23, b23); // embedding

    nnet::relu<embedding_result_t, layer5_t, relu_config5>(layer23_out, layer5_out); // emb_relu

    nnet::pointwise_conv_1d_cl<layer5_t, ffn1_result_t, config27>(layer5_out, layer24_out, w24, b24); // ffn1

    nnet::relu<ffn1_result_t, layer9_t, relu_config9>(layer24_out, layer9_out); // ffn_relu

    nnet::pointwise_conv_1d_cl<layer9_t, ffn2_result_t, config28>(layer9_out, layer25_out, w25, b25); // ffn2

    nnet::add<layer5_t, ffn2_result_t, ffn_add_result_t, config12>(layer5_out, layer25_out, layer12_out); // ffn_add

    nnet::normalize<ffn_add_result_t, final_bn_result_t, config13>(layer12_out, layer13_out, s13, b13); // final_bn

    nnet::global_pooling1d_cl<final_bn_result_t, layer14_t, config14>(layer13_out, layer14_out); // global_pool

    nnet::dense<layer14_t, se_dense1_result_t, config15>(layer14_out, layer15_out, w15, b15); // se_dense1

    nnet::relu<se_dense1_result_t, layer16_t, relu_config16>(layer15_out, layer16_out); // se_dense1_relu

    nnet::dense<layer16_t, se_dense2_result_t, config17>(layer16_out, layer17_out, w17, b17); // se_dense2

    nnet::sigmoid<se_dense2_result_t, layer18_t, sigmoid_config18>(layer17_out, layer18_out); // se_dense2_sigmoid

    nnet::multiply<layer14_t, layer18_t, se_mult_result_t, config19>(layer14_out, layer18_out, layer19_out); // se_mult

    nnet::add<layer14_t, se_mult_result_t, se_add_result_t, config20>(layer14_out, layer19_out, layer20_out); // se_add

    nnet::dense<se_add_result_t, result_t, config21>(layer20_out, layer21_out, w21, b21); // output_logits

}

