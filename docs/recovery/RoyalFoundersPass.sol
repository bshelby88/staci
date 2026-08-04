// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title RoyalFoundersPass (DiamondPass)
 * @notice Limited 100-Pass Founder NFT on Base Network
 * @dev Mints at 0.1 ETH per pass. Revenue routed to wallet 0x9e6A.
 */
contract RoyalFoundersPass is ERC721, Ownable {
    uint256 public constant MAX_SUPPLY = 100;
    uint256 public constant MINT_PRICE = 0.1 ether;
    uint256 public totalSupply;
    address payable public immutable treasury;

    event PassMinted(address indexed minter, uint256 indexed tokenId);

    constructor(address payable _treasury) ERC721("Royal Founders Pass", "RFP") Ownable(msg.sender) {
        require(_treasury != address(0), "Invalid treasury address");
        treasury = _treasury;
    }

    function mintPass() external payable {
        require(totalSupply < MAX_SUPPLY, "Max supply reached");
        require(msg.value >= MINT_PRICE, "Insufficient ETH sent");

        totalSupply++;
        uint256 newTokenId = totalSupply;
        _safeMint(msg.sender, newTokenId);

        (bool success, ) = treasury.call{value: msg.value}("");
        require(success, "Treasury transfer failed");

        emit PassMinted(msg.sender, newTokenId);
    }
}
