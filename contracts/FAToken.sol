// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * Учебный ERC-20 токен FA для проекта Telegram Web3 Advisor.
 * Деплой: Sepolia (рекомендуется) или другая EVM-сеть с тем же chainId, что и WEB3_RPC_URL.
 *
 * - При деплое 1_000_000 FA минтится на адрес деплоера.
 * - mint() только владельцем — можно раздавать токены студентам для демо.
 */
contract FAToken {
    string public constant name = "FA Token";
    string public constant symbol = "FA";
    uint8 public constant decimals = 18;

    uint256 public totalSupply;
    address public owner;

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    error InsufficientBalance();
    error InsufficientAllowance();
    error NotOwner();

    constructor() {
        owner = msg.sender;
        uint256 initial = 1_000_000 * 10 ** uint256(decimals);
        totalSupply = initial;
        balanceOf[msg.sender] = initial;
        emit Transfer(address(0), msg.sender, initial);
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        uint256 allowed = allowance[from][msg.sender];
        if (allowed < amount) revert InsufficientAllowance();
        unchecked {
            allowance[from][msg.sender] = allowed - amount;
        }
        _transfer(from, to, amount);
        return true;
    }

    /// @notice Только владелец контракта. Для учебного «крана» раздайте FA студентам.
    function mint(address to, uint256 amount) external {
        if (msg.sender != owner) revert NotOwner();
        totalSupply += amount;
        balanceOf[to] += amount;
        emit Transfer(address(0), to, amount);
    }

    function _transfer(address from, address to, uint256 amount) internal {
        if (balanceOf[from] < amount) revert InsufficientBalance();
        unchecked {
            balanceOf[from] -= amount;
            balanceOf[to] += amount;
        }
        emit Transfer(from, to, amount);
    }
}
